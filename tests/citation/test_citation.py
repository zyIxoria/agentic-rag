"""test_citation.py - Bộ kiểm thử đơn vị cho phân hệ Citation Mapping (TASK RAG-06).

Kiểm thử:
1. test_01_valid_single_citation
2. test_02_multiple_citations
3. test_03_invalid_source_number (REJECT INVALID CITATION)
4. test_04_missing_source_in_mapping
5. test_05_citation_metadata_correctness
6. test_06_url_mapping
7. test_07_in_text_replacement_and_footnotes
8. test_08_no_invented_citation
"""

import unittest
from RAG.citation.schema import LegalCitation, CitationResolutionResult
from RAG.citation.resolver import CitationResolver, format_legal_citation


class TestCitationMapping(unittest.TestCase):
    """Test suite cho Citation Mapping."""

    def setUp(self):
        self.resolver = CitationResolver(replace_in_text=True, append_footnotes=True)
        self.sample_mapping = {
            "[SOURCE 1]": {
                "source_id": "[SOURCE 1]",
                "source_number": 1,
                "chunk_id": "chunk_bbld_art125_001",
                "document_title": "Bộ luật Lao động 2019",
                "document_number": "45/2019/QH14",
                "article_number": "Điều 125",
                "article_title": "Áp dụng hình thức xử lý kỷ luật sa thải",
                "clause_number": "Khoản 1",
                "point_number": "Điểm a",
                "source_url": "https://vbpl.vn/bld/Pages/vbpq-toanvan.aspx?ItemID=139260",
                "score": 0.88,
                "rank": 1
            },
            "[SOURCE 2]": {
                "source_id": "[SOURCE 2]",
                "source_number": 2,
                "chunk_id": "chunk_nd145_art005_002",
                "document_title": "Nghị định số 145/2020/NĐ-CP",
                "document_number": "145/2020/NĐ-CP",
                "article_number": "Điều 5",
                "article_title": "Huấn luyện an toàn lao động",
                "clause_number": None,
                "point_number": None,
                "source_url": "https://vbpl.vn/bld/Pages/vbpq-toanvan.aspx?ItemID=145000",
                "score": 0.76,
                "rank": 2
            }
        }

    def test_01_valid_single_citation(self):
        """Kiểm thử ánh xạ 1 nguồn trích dẫn hợp lệ."""
        raw_answer = "Theo quy định tại [SOURCE 1], người sử dụng lao động có quyền áp dụng hình thức sa thải."
        res = self.resolver.resolve_citations(raw_answer, self.sample_mapping)

        self.assertIsInstance(res, CitationResolutionResult)
        self.assertEqual(res.citations_count, 1)
        self.assertFalse(res.has_invalid_citations)
        self.assertEqual(len(res.valid_citations), 1)

        cit = res.valid_citations[0]
        self.assertEqual(cit.source_id, "[SOURCE 1]")
        self.assertEqual(cit.document_title, "Bộ luật Lao động 2019")
        self.assertEqual(cit.document_number, "45/2019/QH14")
        self.assertEqual(cit.article_number, "Điều 125")
        self.assertEqual(cit.clause_number, "Khoản 1")
        self.assertEqual(cit.point_number, "Điểm a")
        self.assertEqual(cit.formatted_citation, "[Bộ luật Lao động 2019, Điều 125, Khoản 1, Điểm a]")
        self.assertIn("[Bộ luật Lao động 2019, Điều 125, Khoản 1, Điểm a]", res.enriched_answer)

    def test_02_multiple_citations(self):
        """Kiểm thử ánh xạ đồng thời nhiều nguồn trích dẫn."""
        raw_answer = "Căn cứ theo [SOURCE 1] và hướng dẫn tại [SOURCE 2], doanh nghiệp phải thực hiện đầy đủ."
        res = self.resolver.resolve_citations(raw_answer, self.sample_mapping)

        self.assertEqual(res.citations_count, 2)
        self.assertFalse(res.has_invalid_citations)
        self.assertEqual(len(res.valid_citations), 2)
        self.assertIn("[Bộ luật Lao động 2019, Điều 125, Khoản 1, Điểm a]", res.enriched_answer)
        self.assertIn("[Nghị định số 145/2020/NĐ-CP, Điều 5]", res.enriched_answer)

    def test_03_invalid_source_number(self):
        """Kiểm thử trường hợp LLM sinh nguồn ảo [SOURCE 99] (REJECT INVALID CITATION)."""
        raw_answer = "Theo [SOURCE 1] và [SOURCE 99], người lao động được hưởng chế độ đặc biệt."
        res = self.resolver.resolve_citations(raw_answer, self.sample_mapping)

        self.assertTrue(res.has_invalid_citations)
        self.assertEqual(res.invalid_citations, ["[SOURCE 99]"])
        self.assertEqual(res.citations_count, 1)  # Chỉ có SOURCE 1 hợp lệ
        # Kiểm tra không được render citation giả cho SOURCE 99
        self.assertNotIn("SOURCE 99", res.enriched_answer)
        self.assertIn("[Bộ luật Lao động 2019, Điều 125, Khoản 1, Điểm a]", res.enriched_answer)

    def test_04_missing_source_in_mapping(self):
        """Kiểm thử trường hợp trích dẫn thẻ không có trong mapping."""
        raw_answer = "Theo quy định tại [SOURCE 5], lương làm thêm giờ..."
        res = self.resolver.resolve_citations(raw_answer, self.sample_mapping, citations_list=["SOURCE 5"])

        self.assertTrue(res.has_invalid_citations)
        self.assertEqual(res.citations_count, 0)
        self.assertIn("[SOURCE 5]", res.invalid_citations)

    def test_05_citation_metadata_correctness(self):
        """Kiểm tra tính chuẩn xác của hàm format_legal_citation với các cấp độ metadata."""
        meta_full = {
            "document_title": "Bộ luật Lao động 2019",
            "article_number": "Điều 105",
            "clause_number": "Khoản 2",
            "point_number": "Điểm b"
        }
        self.assertEqual(
            format_legal_citation(meta_full),
            "[Bộ luật Lao động 2019, Điều 105, Khoản 2, Điểm b]"
        )

        meta_no_point = {
            "document_title": "Luật Việc làm 2013",
            "article_number": "Điều 43",
            "clause_number": "Khoản 1"
        }
        self.assertEqual(
            format_legal_citation(meta_no_point),
            "[Luật Việc làm 2013, Điều 43, Khoản 1]"
        )

        meta_art_only = {
            "document_title": "Nghị định 152/2020/NĐ-CP",
            "article_number": "12"  # Tự động chuẩn hóa thêm chữ 'Điều'
        }
        self.assertEqual(
            format_legal_citation(meta_art_only),
            "[Nghị định 152/2020/NĐ-CP, Điều 12]"
        )

    def test_06_url_mapping(self):
        """Kiểm thử ánh xạ chính xác URL tra cứu văn bản pháp quy từ metadata."""
        raw_answer = "Theo [SOURCE 1], sa thải được quy định tại điều này."
        res = self.resolver.resolve_citations(raw_answer, self.sample_mapping)

        cit = res.valid_citations[0]
        self.assertEqual(cit.source_url, "https://vbpl.vn/bld/Pages/vbpq-toanvan.aspx?ItemID=139260")
        # Footnotes phải chứa URL
        self.assertTrue(any(cit.source_url in fn for fn in res.footnotes))
        self.assertIn("https://vbpl.vn/bld/Pages/vbpq-toanvan.aspx?ItemID=139260", res.enriched_answer)

    def test_07_in_text_replacement_and_footnotes(self):
        """Kiểm thử tùy chọn thay thế nội văn bản và danh mục tham chiếu phụ lục."""
        raw_answer = "Theo [SOURCE 2], doanh nghiệp phải tổ chức huấn luyện an toàn."
        
        # Bật thay thế in-text & footnotes
        res = self.resolver.resolve_citations(raw_answer, self.sample_mapping, replace_in_text=True, append_footnotes=True)
        self.assertIn("[Nghị định số 145/2020/NĐ-CP, Điều 5]", res.enriched_answer)
        self.assertIn("Căn Cứ Pháp Lý Tham Chiếu:", res.enriched_answer)

        # Tắt thay thế in-text
        res_no_repl = self.resolver.resolve_citations(raw_answer, self.sample_mapping, replace_in_text=False, append_footnotes=False)
        self.assertIn("[SOURCE 2]", res_no_repl.enriched_answer)
        self.assertNotIn("Căn Cứ Pháp Lý Tham Chiếu:", res_no_repl.enriched_answer)

    def test_08_no_invented_citation(self):
        """Kiểm tra tuyệt đối không bịa đặt số hiệu hay điều luật cho nguồn invalid."""
        raw_answer = "Căn cứ theo [SOURCE 404], quy định mới có hiệu lực."
        res = self.resolver.resolve_citations(raw_answer, self.sample_mapping)

        self.assertEqual(res.valid_citations, [])
        self.assertTrue(res.has_invalid_citations)
        self.assertNotIn("404", res.enriched_answer)


if __name__ == "__main__":
    unittest.main()
