"""
Unit tests for RAG-08 Legal RAG Evaluation Dataset.

Verifies:
1. JSON Schema conformance (schema.json vs legal_qa.json)
2. Target dataset size (>= 50 questions, target 80-120)
3. Full representation of all 7 categories (A through G)
4. 100% gold-source traceability to Dataset V2.1 chunk IDs
5. Refusal question semantics (insufficient evidence & out-of-scope)
6. Uniqueness of question IDs and question content
7. Data quality and grounding integrity
"""

import json
from pathlib import Path
import unittest
import jsonschema


class TestLegalEvaluationDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_dir = Path(__file__).resolve().parent.parent.parent
        cls.schema_path = cls.root_dir / "evaluation" / "dataset" / "schema.json"
        cls.dataset_path = cls.root_dir / "evaluation" / "dataset" / "legal_qa.json"
        cls.corpus_path = cls.root_dir / "Data_Processing" / "output_v2" / "legal_dataset_v2.json"

        # Load schema
        with open(cls.schema_path, "r", encoding="utf-8") as f:
            cls.schema = json.load(f)

        # Load dataset
        with open(cls.dataset_path, "r", encoding="utf-8") as f:
            cls.dataset = json.load(f)

        # Load corpus chunk IDs
        with open(cls.corpus_path, "r", encoding="utf-8") as f:
            corpus_data = json.load(f)
            cls.corpus_chunk_ids = {chunk["chunk_id"] for chunk in corpus_data}
            cls.corpus_doc_ids = {chunk["document_id"] for chunk in corpus_data}

    def test_schema_conformance(self):
        """Verify legal_qa.json passes JSON schema validation."""
        jsonschema.validate(instance=self.dataset, schema=self.schema)

    def test_dataset_size(self):
        """Verify dataset satisfies the size requirements (>= 50 questions)."""
        count = len(self.dataset)
        self.assertGreaterEqual(count, 50, f"Dataset must contain at least 50 questions, found {count}")
        self.assertEqual(count, 80, f"Target benchmark size is 80 questions, found {count}")

    def test_all_categories_represented(self):
        """Verify all 7 question categories are properly populated."""
        expected_categories = {
            "single_article",
            "single_doc_multi_chunk",
            "multi_document",
            "cross_reference",
            "complex_conditions",
            "insufficient_evidence",
            "out_of_scope",
        }
        present_categories = {item["category"] for item in self.dataset}
        self.assertEqual(expected_categories, present_categories, "All 7 categories must be present in the dataset")

        # Check counts per category
        category_counts = {}
        for item in self.dataset:
            category_counts[item["category"]] = category_counts.get(item["category"], 0) + 1

        self.assertGreaterEqual(category_counts["single_article"], 10)
        self.assertGreaterEqual(category_counts["single_doc_multi_chunk"], 10)
        self.assertGreaterEqual(category_counts["multi_document"], 10)
        self.assertGreaterEqual(category_counts["cross_reference"], 8)
        self.assertGreaterEqual(category_counts["complex_conditions"], 10)
        self.assertGreaterEqual(category_counts["insufficient_evidence"], 5)
        self.assertGreaterEqual(category_counts["out_of_scope"], 5)

    def test_gold_sources_traceability(self):
        """Verify 100% of gold chunk IDs exist in Dataset V2.1."""
        total_gold_chunks = 0
        missing_chunks = []

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
                        total_gold_chunks += 1
                        if cid not in self.corpus_chunk_ids:
                            missing_chunks.append((item["question_id"], cid))

        self.assertEqual(
            missing_chunks, [],
            f"Found {len(missing_chunks)} gold chunk IDs not present in Dataset V2.1: {missing_chunks[:5]}"
        )
        self.assertGreater(total_gold_chunks, 100, f"Expected >100 gold chunk references, found {total_gold_chunks}")

    def test_refusal_questions_policy(self):
        """Verify insufficient_evidence and out_of_scope questions require refusal."""
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

    def test_unique_ids_and_questions(self):
        """Verify no duplicate question IDs or duplicate question contents."""
        question_ids = [item["question_id"] for item in self.dataset]
        self.assertEqual(len(question_ids), len(set(question_ids)), "Found duplicate question IDs")

        question_texts = [item["question"].strip().lower() for item in self.dataset]
        self.assertEqual(len(question_texts), len(set(question_texts)), "Found duplicate question texts")

    def test_quality_and_field_integrity(self):
        """Verify all fields meet quality standards and non-emptiness."""
        for item in self.dataset:
            qid = item["question_id"]
            self.assertTrue(qid.startswith("Q") and qid[1:].isdigit(), f"Invalid question_id format: {qid}")
            self.assertGreater(len(item["question"].strip()), 15, f"Question {qid} is too short")
            self.assertGreater(len(item["reference_answer"].strip()), 15, f"Reference answer {qid} is too short")


if __name__ == "__main__":
    unittest.main()
