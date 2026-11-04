"""benchmark_embeddings_vi.py - Thực nghiệm và Đánh giá độc lập các mô hình Embedding tiếng Việt.

So sánh 4 mô hình:
1. sentence-transformers/all-MiniLM-L6-v2 (Baseline hiện tại, 384d)
2. bkai-foundation-models/vietnamese-bi-encoder (Mô hình Bi-Encoder tiếng Việt chuyên dụng, 768d)
3. BAAI/bge-m3 (Mô hình đa ngữ tiên tiến SOTA, 1024d)
4. vinai/phobert-base (Mô hình nền tảng tiếng Việt nguyên bản PhoBERT, 768d)

Đo lường các chỉ số:
- Hit@1, Hit@3, Hit@5
- MRR@5 (Mean Reciprocal Rank)
- Precision@5
- Margin phân biệt ngữ nghĩa: Delta = Sim(Query, Positive) - Sim(Query, Distractor)
- Latency (thời gian sinh vector trung bình trên CPU)
- Dimension và footprint
"""

from __future__ import annotations
import os
import sys
import time
import json
import logging
from typing import List, Dict, Any, Tuple
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EmbeddingBenchmark")


def l2_normalize(vecs: np.ndarray) -> np.ndarray:
    """Chuẩn hóa L2 cho ma trận vector."""
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-12, norms)
    return vecs / norms


def load_dataset(corpus_path: str, queries_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Nạp dataset chunks và benchmark queries."""
    with open(corpus_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    with open(queries_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    return chunks, queries


def build_candidate_pool(chunks: List[Dict[str, Any]], queries: List[Dict[str, Any]], pool_size: int = 250) -> List[Dict[str, Any]]:
    """Xây dựng tập ứng viên chứa toàn bộ Gold Positive + Hard Negative + Chunks phân tán đều 19 văn bản."""
    critical_ids = set()
    for q in queries:
        for cid in q.get("relevant_chunk_ids", []):
            critical_ids.add(cid)
        for cid in q.get("hard_negative_chunk_ids", []):
            critical_ids.add(cid)

    critical_chunks = [c for c in chunks if c["chunk_id"] in critical_ids]
    remaining_chunks = [c for c in chunks if c["chunk_id"] not in critical_ids]

    rng = np.random.RandomState(42)
    needed = max(0, pool_size - len(critical_chunks))
    sample_indices = rng.choice(len(remaining_chunks), size=min(needed, len(remaining_chunks)), replace=False)
    sampled_remaining = [remaining_chunks[i] for i in sample_indices]

    pool = critical_chunks + sampled_remaining
    logger.info(f"Đã tạo candidate pool: {len(pool)} chunks (gồm {len(critical_chunks)} chunks cốt lõi & {len(sampled_remaining)} chunks nền).")
    return pool


class ModelEvaluator:
    """Đánh giá chi tiết một mô hình embedding trên tập dữ liệu chuẩn."""

    def __init__(self, name: str, hf_path: str, max_seq_length: int = 512):
        self.name = name
        self.hf_path = hf_path
        self.max_seq_length = max_seq_length
        self.model = None
        self.dimension = 0

    def load(self):
        """Khởi tạo mô hình SentenceTransformer với cấu hình tối ưu."""
        from sentence_transformers import SentenceTransformer
        t0 = time.time()
        self.model = SentenceTransformer(self.hf_path, device="cpu")
        if self.max_seq_length:
            self.model.max_seq_length = self.max_seq_length
            if hasattr(self.model, "tokenizer") and self.model.tokenizer is not None:
                self.model.tokenizer.model_max_length = self.max_seq_length
        self.dimension = self.model.get_embedding_dimension()
        load_time = time.time() - t0
        logger.info(f"Loaded {self.name} (dim={self.dimension}) in {load_time:.2f}s")
        return load_time

    def encode_texts(self, texts: List[str], batch_size: int = 32) -> Tuple[np.ndarray, float]:
        """Sinh vector cho danh sách văn bản và đo lường thời gian."""
        t0 = time.time()
        vecs = self.model.encode(texts, batch_size=batch_size, show_progress_bar=False, normalize_embeddings=True)
        elapsed = time.time() - t0
        return np.asarray(vecs, dtype=np.float32), elapsed


def run_benchmark(corpus_file: str, queries_file: str, output_file: str):
    """Quy trình thực nghiệm toàn diện."""
    chunks, queries = load_dataset(corpus_file, queries_file)
    candidate_pool = build_candidate_pool(chunks, queries, pool_size=250)

    corpus_texts = [c["content"] for c in candidate_pool]
    corpus_ids = [c["chunk_id"] for c in candidate_pool]
    id2idx = {cid: idx for idx, cid in enumerate(corpus_ids)}

    query_texts = [q["query"] for q in queries]

    models_config = [
        ("all-MiniLM-L6-v2", "sentence-transformers/all-MiniLM-L6-v2", 512),
        ("bkai-vietnamese-bi-encoder", "bkai-foundation-models/vietnamese-bi-encoder", 256),
        ("bge-m3", "BAAI/bge-m3", 512),
        ("phobert-base", "vinai/phobert-base", 256),
    ]

    all_results = {}

    for name, hf_path, max_len in models_config:
        logger.info(f"\n{'='*20} BẮT ĐẦU ĐÁNH GIÁ: {name} {'='*20}")
        evaluator = ModelEvaluator(name, hf_path, max_seq_length=max_len)
        load_time = evaluator.load()

        # 1. Sinh vector cho candidate pool (Document Encoding)
        corpus_vectors, corpus_time = evaluator.encode_texts(corpus_texts, batch_size=32)
        latency_per_doc = (corpus_time / len(corpus_texts)) * 1000  # ms/doc

        # 2. Sinh vector cho Queries
        query_vectors, query_time = evaluator.encode_texts(query_texts, batch_size=16)

        # 3. Tính ma trận Cosine Similarity: [num_queries, num_docs]
        sim_matrix = np.matmul(query_vectors, corpus_vectors.T)

        # 4. Đánh giá từng Query
        hits_at_1 = 0
        hits_at_3 = 0
        hits_at_5 = 0
        reciprocal_ranks = []
        precisions_at_5 = []

        query_detailed_results = []
        semantic_margins = []

        for q_idx, q in enumerate(queries):
            qid = q["query_id"]
            q_text = q["query"]
            gold_ids = set(q.get("relevant_chunk_ids", []))
            hard_neg_ids = set(q.get("hard_negative_chunk_ids", []))

            scores = sim_matrix[q_idx]
            ranked_indices = np.argsort(-scores)
            ranked_ids = [corpus_ids[i] for i in ranked_indices]

            first_gold_rank = None
            gold_in_top5 = 0

            for r, cid in enumerate(ranked_ids[:10], start=1):
                if cid in gold_ids:
                    if first_gold_rank is None:
                        first_gold_rank = r
                    if r <= 5:
                        gold_in_top5 += 1

            h1 = 1 if (first_gold_rank and first_gold_rank <= 1) else 0
            h3 = 1 if (first_gold_rank and first_gold_rank <= 3) else 0
            h5 = 1 if (first_gold_rank and first_gold_rank <= 5) else 0

            hits_at_1 += h1
            hits_at_3 += h3
            hits_at_5 += h5

            rr = 1.0 / first_gold_rank if first_gold_rank else 0.0
            reciprocal_ranks.append(rr)

            p5 = gold_in_top5 / 5.0
            precisions_at_5.append(p5)

            pos_scores = [float(scores[id2idx[cid]]) for cid in gold_ids if cid in id2idx]
            neg_scores = [float(scores[id2idx[cid]]) for cid in hard_neg_ids if cid in id2idx]

            avg_pos = np.mean(pos_scores) if pos_scores else 0.0
            avg_neg = np.mean(neg_scores) if neg_scores else 0.0
            margin = avg_pos - avg_neg
            semantic_margins.append(margin)

            top5_preview = [
                {
                    "rank": r + 1,
                    "chunk_id": ranked_ids[r],
                    "score": round(float(scores[ranked_indices[r]]), 4),
                    "is_gold": ranked_ids[r] in gold_ids,
                    "is_hard_negative": ranked_ids[r] in hard_neg_ids,
                }
                for r in range(min(5, len(ranked_ids)))
            ]

            query_detailed_results.append({
                "query_id": qid,
                "query": q_text,
                "first_gold_rank": first_gold_rank,
                "mrr": round(rr, 4),
                "avg_pos_score": round(float(avg_pos), 4),
                "avg_neg_score": round(float(avg_neg), 4),
                "margin": round(float(margin), 4),
                "top5": top5_preview,
            })

        n_queries = len(queries)
        summary = {
            "model_name": name,
            "hf_path": hf_path,
            "dimension": evaluator.dimension,
            "latency_ms_per_doc": round(latency_per_doc, 2),
            "hit_at_1": round(hits_at_1 / n_queries * 100, 2),
            "hit_at_3": round(hits_at_3 / n_queries * 100, 2),
            "hit_at_5": round(hits_at_5 / n_queries * 100, 2),
            "mrr_at_5": round(float(np.mean(reciprocal_ranks)), 4),
            "precision_at_5": round(float(np.mean(precisions_at_5)) * 100, 2),
            "avg_semantic_margin": round(float(np.mean(semantic_margins)), 4),
            "detailed_queries": query_detailed_results,
        }

        logger.info(
            f"Kết quả {name}: Hit@1={summary['hit_at_1']}% | Hit@5={summary['hit_at_5']}% | "
            f"MRR@5={summary['mrr_at_5']} | Margin={summary['avg_semantic_margin']:+.4f} | Latency={latency_per_doc:.1f}ms"
        )
        all_results[name] = summary

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    logger.info(f"\nĐã lưu toàn bộ kết quả thực nghiệm tại: {output_file}")
    return all_results


if __name__ == "__main__":
    corpus_p = "Data_Processing/output_v2/legal_dataset_v2.json"
    queries_p = "evaluation/benchmark_queries_vi.json"
    output_p = "evaluation/benchmark_embedding_results.json"
    run_benchmark(corpus_p, queries_p, output_p)
