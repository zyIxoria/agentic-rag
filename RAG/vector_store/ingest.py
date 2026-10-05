"""ingest.py - Mô-đun nạp (ingestion) toàn bộ Legal Dataset V2.1 vào Persistent Vector Store.

Kết nối đường ống:
Dataset V2.1 (1,390 chunks)
          ↓
RAG-01 LegalEmbeddingPipeline (sentence-transformers/all-MiniLM-L6-v2, 384d)
          ↓
PersistentChromaStore (data/chroma_db, HNSW Cosine, dataset_version='v2.1')
"""

from __future__ import annotations
import os
import json
import time
import logging
from typing import Dict, Any, Optional

from RAG.config import EmbeddingConfig, default_embedding_config
from RAG.embedding import LegalEmbeddingPipeline, get_embedding_provider
from RAG.vector_store.chroma_store import PersistentChromaStore
from RAG.vector_store.schema import VectorRecord

logger = logging.getLogger(__name__)


def ingest_legal_dataset(
    dataset_path: str = "Data_Processing/output_v2/legal_dataset_v2.json",
    persist_directory: str = "data/chroma_db",
    collection_name: str = "legal_labor_baseline_minilm",
    overwrite: bool = True,
    embedding_config: Optional[EmbeddingConfig] = None,
) -> Dict[str, Any]:
    """Thực thi đường ống embedding và nạp dữ liệu bền vững vào ChromaDB.
    
    Args:
        dataset_path: Đường dẫn tệp Dataset V2.1.
        persist_directory: Thư mục lưu trữ database véc-tơ bền vững.
        collection_name: Tên collection trong ChromaDB.
        overwrite: Ghi đè collection nếu đã tồn tại.
        embedding_config: Cấu hình mô hình embedding.
        
    Returns:
        Dict[str, Any]: Báo cáo kết quả nạp dữ liệu.
    """
    start_time = time.perf_counter()

    # 1. Kiểm tra và đọc Dataset V2.1
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Không tìm thấy tệp dataset tại: {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        raw_chunks = json.load(f)

    total_chunks = len(raw_chunks)
    logger.info(f"Đã đọc thành công {total_chunks} chunks từ {dataset_path}.")

    # 2. Khởi tạo Embedding Pipeline từ RAG-01
    cfg = embedding_config or default_embedding_config
    provider = get_embedding_provider(cfg)
    pipeline = LegalEmbeddingPipeline(provider=provider, config=cfg)

    # 3. Khởi tạo Persistent Vector Store
    store = PersistentChromaStore(persist_directory=persist_directory)
    col = store.create_collection(
        name=collection_name,
        embedding_dimension=provider.dimension,
        embedding_model=provider.model_name,
        dataset_version="v2.1",
        distance_metric="cosine",
        metadata={
            "description": "Legal Labor Law Baseline Vector Store",
            "source_dataset": dataset_path,
        },
        overwrite=overwrite,
    )

    # 4. Sinh vector cho toàn bộ chunks (RAG-01 Pipeline)
    logger.info(
        f"Bắt đầu sinh embedding qua {provider.model_name} (dimension={provider.dimension}, device={provider.device})..."
    )
    embedded_chunks = pipeline.process_chunks(raw_chunks)

    # 5. Nạp vào PersistentChromaStore
    ids = [c.chunk_id for c in embedded_chunks]
    embeddings = [c.embedding for c in embedded_chunks]
    documents = [c.content for c in embedded_chunks]
    metadatas = [c.metadata for c in embedded_chunks]

    logger.info(f"Đang nạp {len(ids)} bản ghi vào collection '{collection_name}'...")
    upserted_count = store.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        batch_size=500,
        deduplicate_batch=True,
    )

    # 6. Xác thực tính toàn vẹn (Integrity Validation)
    current_count = store.count()
    if current_count != total_chunks:
        raise RuntimeError(
            f"Số lượng bản ghi trong collection ({current_count}) không khớp tổng số chunks ({total_chunks})!"
        )

    # Thử nghiệm lấy mẫu ngẫu nhiên 3 bản ghi
    sample_ids = [ids[0], ids[len(ids) // 2], ids[-1]]
    for sid in sample_ids:
        record = store.get_by_id(sid)
        if not record or record["id"] != sid:
            raise RuntimeError(f"Không thể truy xuất bản ghi mẫu {sid} sau khi upsert.")

    store.persist()
    elapsed = time.perf_counter() - start_time

    result = {
        "status": "PASS",
        "collection_name": collection_name,
        "persist_directory": os.path.abspath(persist_directory),
        "total_chunks_ingested": upserted_count,
        "collection_count": current_count,
        "embedding_model": provider.model_name,
        "embedding_dimension": provider.dimension,
        "device": provider.device,
        "elapsed_seconds": round(elapsed, 3),
        "throughput_chunks_per_sec": round(total_chunks / elapsed, 2),
    }
    logger.info(f"Hoàn tất nạp dữ liệu: {result}")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    res = ingest_legal_dataset()
    print(json.dumps(res, indent=2, ensure_ascii=False))
