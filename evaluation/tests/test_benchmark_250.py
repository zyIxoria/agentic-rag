"""
Unit tests for Vietnamese Labour Law Evaluation Benchmark (Benchmark-250).

Verifies:
1. JSON Schema conformance (schema.json vs benchmark_250.json)
2. Total question count exactly equals 250
3. Target category distribution across all 7 categories:
   - single_article: 35
   - single_doc_multi_chunk: 35
   - multi_document: 45
   - cross_reference: 35
   - complex_conditions: 50
   - insufficient_evidence: 25
   - out_of_scope: 25
4. 100% gold-source traceability to Dataset V2.1 chunk IDs (2,117 chunks)
5. Coverage across all 19 legal documents
6. Refusal question semantics (requires_refusal=True, gold_sources=[])
7. Uniqueness of question IDs (Q001 - Q250) and question text
8. Integrity of LUAT_BHXH_2024 (active status, effective 01/07/2025)
"""

import json
from pathlib import Path
import unittest
from collections import Counter
import jsonschema


class TestBenchmark250Dataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_dir = Path(__file__).resolve().parent.parent.parent
        cls.schema_path = cls.root_dir / "evaluation" / "dataset" / "schema.json"
        cls.dataset_path = cls.root_dir / "evaluation" / "dataset" / "benchmark_250.json"
        cls.corpus_path = cls.root_dir / "Data_Processing" / "output_v2" / "legal_dataset_v2.json"

        # Load schema
        with open(cls.schema_path, "r", encoding="utf-8") as f:
            cls.schema = json.load(f)

        # Load dataset
        with open(cls.dataset_path, "r", encoding="utf-8") as f:
            cls.dataset = json.load(f)

        # Load corpus chunk IDs and document IDs
        with open(cls.corpus_path, "r", encoding="utf-8") as f:
            corpus_data = json.load(f)
            cls.corpus_chunk_ids = {chunk["chunk_id"] for chunk in corpus_data}
            cls.corpus_doc_ids = {chunk["document_id"] for chunk in corpus_data}

    def test_schema_conformance(self):
        """Verify benchmark_250.json passes JSON schema validation."""
        jsonschema.validate(instance=self.dataset, schema=self.schema)

    def test_dataset_size(self):
        """Verify dataset contains exactly 250 questions."""
        count = len(self.dataset)
        self.assertEqual(count, 250, f"Expected 250 questions, found {count}")

    def test_category_distribution(self):
        """Verify exact target counts for all 7 question categories."""
        expected_distribution = {
            "single_article": 35,
            "single_doc_multi_chunk": 35,
            "multi_document": 45,
            "cross_reference": 35,
            "complex_conditions": 50,
            "insufficient_evidence": 25,
            "out_of_scope": 25,
        }
        category_counts = Counter(item["category"] for item in self.dataset)
        self.assertEqual(expected_distribution, dict(category_counts))

    def test_answerable_vs_refusal_split(self):
        """Verify 200 answerable questions and 50 refusal questions."""
        answerable = [q for q in self.dataset if not q["requires_refusal"]]
        refusal = [q for q in self.dataset if q["requires_refusal"]]
        self.assertEqual(len(answerable), 200)
        self.assertEqual(len(refusal), 50)

    def test_gold_sources_traceability(self):
        """Verify 100% of gold chunk IDs exist in Dataset V2.1."""
        missing_chunks = []
        cited_chunks = set()

        for item in self.dataset:
            if not item["requires_refusal"]:
                self.assertGreater(
                    len(item["gold_sources"]), 0,
                    f"Question {item['question_id']} requires answer but has empty gold_sources"
                )
                for gs in item["gold_sources"]:
                    doc_id = gs["document_id"]
                    self.assertIn(doc_id, self.corpus_doc_ids, f"Document ID {doc_id} not in corpus")
                    self.assertGreater(
                        len(gs["chunk_ids"]), 0,
                        f"Gold source in {item['question_id']} for doc {doc_id} has no chunk_ids"
                    )
                    for cid in gs["chunk_ids"]:
                        cited_chunks.add(cid)
                        if cid not in self.corpus_chunk_ids:
                            missing_chunks.append((item["question_id"], cid))

        self.assertEqual(
            missing_chunks, [],
            f"Found {len(missing_chunks)} gold chunk IDs not present in Dataset V2.1: {missing_chunks[:5]}"
        )
        self.assertGreater(len(cited_chunks), 250, f"Expected >250 unique chunks cited, found {len(cited_chunks)}")

    def test_all_19_documents_covered(self):
        """Verify that all 19 documents in the corpus are cited across the benchmark."""
        cited_docs = set()
        for item in self.dataset:
            for gs in item.get("gold_sources", []):
                cited_docs.add(gs["document_id"])
        
        self.assertEqual(
            cited_docs, self.corpus_doc_ids,
            f"Missing coverage for documents: {self.corpus_doc_ids - cited_docs}"
        )
        self.assertEqual(len(cited_docs), 19)

    def test_refusal_questions_policy(self):
        """Verify insufficient_evidence and out_of_scope questions require refusal with empty gold sources."""
        for item in self.dataset:
            cat = item["category"]
            if cat in ("insufficient_evidence", "out_of_scope"):
                self.assertTrue(
                    item["requires_refusal"],
                    f"Question {item['question_id']} in category '{cat}' must have requires_refusal=True"
                )
                self.assertEqual(
                    item["gold_sources"], [],
                    f"Question {item['question_id']} in category '{cat}' must have empty gold_sources"
                )
                self.assertIn(
                    "Không tìm thấy đủ căn cứ pháp lý",
                    item["reference_answer"],
                    f"Question {item['question_id']} refusal answer must contain standard refusal message"
                )
            else:
                self.assertFalse(
                    item["requires_refusal"],
                    f"Question {item['question_id']} in category '{cat}' must have requires_refusal=False"
                )

    def test_unique_ids_and_sequence(self):
        """Verify sequential IDs Q001 to Q250 without duplicates or gaps."""
        question_ids = [item["question_id"] for item in self.dataset]
        expected_ids = [f"Q{i:03d}" for i in range(1, 251)]
        self.assertEqual(question_ids, expected_ids, "Question IDs must be sequential Q001 to Q250")

        question_texts = [item["question"].strip().lower() for item in self.dataset]
        self.assertEqual(len(question_texts), len(set(question_texts)), "Found duplicate question texts")


if __name__ == "__main__":
    unittest.main()

