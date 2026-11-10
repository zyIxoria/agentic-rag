"""build_vietnamese_vector_store.py - Xây dựng Vector Store ChromaDB cho mô hình Embedding tiếng Việt.

Sử dụng:
- Mô hình: bkai-foundation-models/vietnamese-bi-encoder (768 chiều)
- Dataset: Data_Processing/output_v2/legal_dataset_v2.json (2,117 chunks)
- Vector DB: data/chroma_db
- Collection: legal_labor_vietnamese_bi_encoder
"""

import os
import sys
import time
import json
import logging
from pathlib import Path

# Thêm project root vào sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

os.environ["HF_HUB_OFFLINE"] = "1"

from RAG.config import EmbeddingConfig
from RAG.embedding.embeddings import SentenceTransformerEmbeddingProvider, l2_normalize_batch
from RAG.vector_store.chroma_store import PersistentChromaStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BuildVietnameseStore")

def main():
    dataset_path = "Data_Processing/output_v2/legal_dataset_v2.json"
    persist_dir = "data/chroma_db"
    collection_name = "legal_labor_vietnamese_bi_encoder"
    model_name = "bkai-foundation-models/vietnamese-bi-encoder"
    batch_size = 64

    logger.info(f"Đang nạp dataset từ {dataset_path}...")
    with open(dataset_path, "r", encoding="utf-8") as f:
        raw_chunks = json.load(f)
    total = len(raw_chunks)
    logger.info(f"Tổng số chunks: {total}")

    logger.info(f"Khởi tạo mô hình embedding tiếng Việt: {model_name}...")
    provider = SentenceTransformerEmbeddingProvider(
        model_name=model_name,
        device="cpu",
        batch_size=batch_size,
        normalize_embeddings=True,
    )
    dim = provider.dimension
    logger.info(f"Mô hình đã sẵn sàng: {provider.model_name} (dimension={dim})")

    logger.info(f"Khởi tạo ChromaDB tại {persist_dir}...")
    store = PersistentChromaStore(persist_directory=persist_dir)
    store.create_collection(
        name=collection_name,
        embedding_dimension=dim,
        embedding_model=model_name,
        dataset_version="v2.1",
        distance_metric="cosine",
        metadata={
            "description": "Vietnamese Legal Vector Store using bkai-bi-encoder (768d)",
            "source_dataset": dataset_path,
        },
        overwrite=True,
    )

    # Sinh embedding theo batch
    logger.info("Bắt đầu sinh embedding và nạp vào ChromaDB...")
    t0 = time.time()
    
    texts = [c["content"] for c in raw_chunks]
    ids = [c["chunk_id"] for c in raw_chunks]
    metadatas = []
    
    # Chuẩn bị metadata
    for c in raw_chunks:
        meta = {
            "chunk_id": str(c.get("chunk_id", "")),
            "document_id": str(c.get("document_id", "")),
            "document_title": str(c.get("document_title", "")),
            "article_number": str(c.get("article_number", "")),
            "article_title": str(c.get("article_title", "")),
            "issue_date": str(c.get("issue_date", "")),
            "effective_from": str(c.get("effective_from", "")),
            "effective_to": str(c.get("effective_to", "") or ""),
            "legal_status": str(c.get("legal_status", "")),
            "source_url": str(c.get("source_url", "")),
            "parent_document": str(c.get("parent_document", "")),
            "parent_article": str(c.get("parent_article", "")),
        }
        metadatas.append(meta)

    # Thực hiện theo từng batch để tối ưu bộ nhớ và cập nhật tiến trình
    all_embeddings = []
    for i in range(0, total, batch_size):
        b_texts = texts[i : i + batch_size]
        b_vecs = provider.embed_texts(b_texts)
        all_embeddings.extend(b_vecs)
        logger.info(f"Đã embedding: {min(i + batch_size, total)}/{total} chunks ({(time.time()-t0):.1f}s)")

    logger.info("Đang nạp toàn bộ vector và metadata vào ChromaDB...")
    store.upsert(
        ids=ids,
        embeddings=all_embeddings,
        documents=texts,
        metadatas=metadatas,
        batch_size=500,
        deduplicate_batch=True,
    )

    elapsed = time.time() - t0
    count = store.count()
    logger.info(f"Hoàn thành xuất sắc! Đã nạp {count} chunks vào collection '{collection_name}' trong {elapsed:.2f}s ({elapsed/total*1000:.1f} ms/doc).")

if __name__ == "__main__":
    main()
