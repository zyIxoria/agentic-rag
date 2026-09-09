"""test_hierarchy_parser.py - Unit tests for Context-Aware Legal Hierarchy Parser.

Kiểm thử các yêu cầu của TASK DATA-03:
1. Valid chapter heading (CHƯƠNG I, Chương I, CHƯƠNG 1, Chương 1)
2. Lowercase heading (chương i, chương 1)
3. Chapter reference (theo quy định tại Chương XI, quy định tại Chương III)
4. Chapter reference giữa câu & ngắt dòng (Mục 1 / Chương XI)
5. Mục 1 (Valid section heading và title)
6. Chapter / Section không tồn tại (Chương Mỹ, Chương trình, Mục đích, Mục tiêu)
7. Article trước và sau Chapter transition
8. Khắc phục dứt điểm bug BLLD 2019 (Điều 3 -> Điều 8 không bị gán thành Chương XI)
9. Bảo toàn 100% text (không làm mất text)
10. Xử lý trường hợp "Điều" bị ngắt 2 dòng
"""

import unittest
from Data_Processing.hierarchy_parser import (
    HierarchyParser,
    ChapterInfo,
    SectionInfo,
    ArticleBlock
)


class TestHierarchyParser(unittest.TestCase):
    """Bộ kiểm thử đơn vị cho HierarchyParser."""

    def setUp(self):
        self.parser = HierarchyParser()

    def test_01_valid_chapter_headings(self):
        """Kiểm thử các dạng tiêu đề Chương hợp lệ: số La Mã, số Ả Rập, viết hoa, viết hoa chữ cái đầu."""
        text_roman = (
            "CHƯƠNG I\n"
            "NHỮNG QUY ĐỊNH CHUNG\n\n"
            "Điều 1. Phạm vi điều chỉnh\n"
            "Bộ luật này quy định..."
        )
        doc = self.parser.parse(text_roman)
        self.assertEqual(len(doc.chapters), 1)
        self.assertEqual(doc.chapters[0].number, "Chương I")
        self.assertEqual(doc.chapters[0].title, "NHỮNG QUY ĐỊNH CHUNG")
        self.assertEqual(doc.articles[0].chapter_number, "Chương I")
        self.assertEqual(doc.articles[0].chapter_title, "NHỮNG QUY ĐỊNH CHUNG")

        text_arabic = (
            "Chương 1. Những quy định chung\n\n"
            "Điều 1. Phạm vi điều chỉnh\n"
            "Văn bản này quy định..."
        )
        doc2 = self.parser.parse(text_arabic)
        self.assertEqual(len(doc2.chapters), 1)
        self.assertEqual(doc2.chapters[0].number, "Chương 1")
        self.assertEqual(doc2.chapters[0].title, "Những quy định chung")

        text_colon = (
            "CHƯƠNG 2: HỢP ĐỒNG LAO ĐỘNG\n\n"
            "Điều 2. Giao kết\n"
            "Nội dung..."
        )
        doc3 = self.parser.parse(text_colon)
        self.assertEqual(doc3.chapters[0].number, "Chương 2")
        self.assertEqual(doc3.chapters[0].title, "HỢP ĐỒNG LAO ĐỘNG")

    def test_02_lowercase_chapter_heading(self):
        """Kiểm thử tiêu đề Chương viết thường (chương i, chương 1)."""
        text_lower = (
            "chương i\n"
            "những quy định chung\n\n"
            "Điều 1. Quy định chung\n"
            "Nội dung..."
        )
        doc = self.parser.parse(text_lower)
        self.assertEqual(len(doc.chapters), 1)
        self.assertEqual(doc.chapters[0].number, "Chương i")
        self.assertEqual(doc.chapters[0].title, "những quy định chung")
        self.assertEqual(doc.articles[0].chapter_number, "Chương i")

        text_lower_num = (
            "chương 3 - tiền lương\n\n"
            "Điều 5. Tiền lương\n"
            "Nội dung..."
        )
        doc2 = self.parser.parse(text_lower_num)
        self.assertEqual(doc2.chapters[0].number, "Chương 3")
        self.assertEqual(doc2.chapters[0].title, "tiền lương")

    def test_03_chapter_reference_not_heading(self):
        """Kiểm thử tham chiếu pháp luật không được nhận diện thành heading mới."""
        text_refs = (
            "Chương I\n"
            "QUY ĐỊNH CHUNG\n\n"
            "Điều 1. Áp dụng\n"
            "1. Người lao động thực hiện theo quy định tại Chương XI.\n"
            "2. Chế độ kỷ luật được quy định tại Chương III của Bộ luật này.\n"
            "3. Vi phạm theo Chương IV sẽ bị xử lý."
        )
        doc = self.parser.parse(text_refs)
        # Chỉ có duy nhất Chương I được ghi nhận, không có Chương XI, Chương III, Chương IV
        self.assertEqual(len(doc.chapters), 1)
        self.assertEqual(doc.chapters[0].number, "Chương I")
        self.assertEqual(len(doc.articles), 1)
        self.assertEqual(doc.articles[0].chapter_number, "Chương I")
        # Kiểm tra nội dung text chứa các tham chiếu không bị mất
        self.assertIn("theo quy định tại Chương XI", doc.articles[0].raw_text)
        self.assertIn("quy định tại Chương III", doc.articles[0].raw_text)
        self.assertIn("theo Chương IV", doc.articles[0].raw_text)

    def test_04_chapter_reference_mid_sentence_and_line_wrap(self):
        """Kiểm thử tham chiếu bị ngắt dòng giữa câu (Mục 1 / Chương XI) như trong BLLD 2019 Điều 3."""
        text_wrap = (
            "Chương I\n"
            "NHỮNG QUY ĐỊNH CHUNG\n\n"
            "Điều 3. Giải thích từ ngữ\n"
            "1. Độ tuổi lao động tối thiểu của người lao động là đủ 15 tuổi, trừ trường hợp quy định tại Mục 1\n"
            "Chương XI của Bộ luật này.\n"
            "2. Người sử dụng lao động là doanh nghiệp, cơ quan, tổ chức...\n\n"
            "Điều 4. Chính sách của Nhà nước về lao động\n"
            "1. Bảo đảm quyền làm việc..."
        )
        doc = self.parser.parse(text_wrap)
        # Không được tạo ra Chương XI
        chapter_numbers = [c.number for c in doc.chapters]
        self.assertNotIn("Chương XI", chapter_numbers)
        self.assertEqual(len(doc.chapters), 1)
        self.assertEqual(doc.chapters[0].number, "Chương I")

        # Điều 3 và Điều 4 đều phải thuộc Chương I
        self.assertEqual(doc.articles[0].number, "Điều 3")
        self.assertEqual(doc.articles[0].chapter_number, "Chương I")
        self.assertEqual(doc.articles[1].number, "Điều 4")
        self.assertEqual(doc.articles[1].chapter_number, "Chương I")

        # Text tham chiếu phải còn nguyên vẹn trong Điều 3
        self.assertIn("Chương XI của Bộ luật này.", doc.articles[0].raw_text)

    def test_05_section_heading_muc_1(self):
        """Kiểm thử tiêu đề Mục hợp lệ (Mục 1, MỤC 2) và bóc tách tiêu đề."""
        text_section = (
            "Chương III\n"
            "HỢP ĐỒNG LAO ĐỘNG\n\n"
            "Mục 1. GIAO KẾT HỢP ĐỒNG LAO ĐỘNG\n\n"
            "Điều 13. Hợp đồng lao động\n"
            "Hợp đồng lao động là sự thỏa thuận...\n\n"
            "Mục 2\n"
            "THỰC HIỆN HỢP ĐỒNG LAO ĐỘNG\n\n"
            "Điều 28. Thực hiện công việc\n"
            "Người lao động thực hiện..."
        )
        doc = self.parser.parse(text_section)
        self.assertEqual(len(doc.sections), 2)
        self.assertEqual(doc.sections[0].number, "Mục 1")
        self.assertEqual(doc.sections[0].title, "GIAO KẾT HỢP ĐỒNG LAO ĐỘNG")
        self.assertEqual(doc.sections[1].number, "Mục 2")
        self.assertEqual(doc.sections[1].title, "THỰC HIỆN HỢP ĐỒNG LAO ĐỘNG")

        # Điều 13 thuộc Mục 1, Điều 28 thuộc Mục 2
        self.assertEqual(doc.articles[0].number, "Điều 13")
        self.assertEqual(doc.articles[0].section_number, "Mục 1")
        self.assertEqual(doc.articles[0].section_title, "GIAO KẾT HỢP ĐỒNG LAO ĐỘNG")

        self.assertEqual(doc.articles[1].number, "Điều 28")
        self.assertEqual(doc.articles[1].section_number, "Mục 2")
        self.assertEqual(doc.articles[1].section_title, "THỰC HIỆN HỢP ĐỒNG LAO ĐỘNG")

    def test_06_section_reference_not_heading(self):
        """Kiểm thử tham chiếu đến Mục không biến thành Section heading mới."""
        text_sec_ref = (
            "Chương I\n"
            "QUY ĐỊNH CHUNG\n\n"
            "Điều 1. Phạm vi\n"
            "Trừ trường hợp quy định tại Mục 1 của Chương này.\n"
            "Nội dung tiếp theo theo Mục 2 sẽ được hướng dẫn sau."
        )
        doc = self.parser.parse(text_sec_ref)
        self.assertEqual(len(doc.sections), 0)  # Không có section heading nào
        self.assertEqual(doc.articles[0].section_number, None)

    def test_07_invalid_chapter_and_section_patterns(self):
        """Kiểm thử từ chối các từ bắt đầu bằng Chương hoặc Mục nhưng không phải heading (Chương Mỹ, Chương trình, Mục đích)."""
        text_false_words = (
            "Chương I\n"
            "QUY ĐỊNH CHUNG\n\n"
            "Điều 1. Địa bàn áp dụng\n"
            "1. Huyện Chương Mỹ và thị xã Sơn Tây thuộc thành phố Hà Nội.\n"
            "2. Chương trình mục tiêu quốc gia về việc làm.\n"
            "3. Mục đích của quy định này là bảo vệ quyền lợi người lao động.\n"
            "4. Mục tiêu tăng trưởng tiền lương năm 2026."
        )
        doc = self.parser.parse(text_false_words)
        # Chỉ có 1 Chương I, không bị nhầm Chương Mỹ hay Chương trình
        self.assertEqual(len(doc.chapters), 1)
        self.assertEqual(doc.chapters[0].number, "Chương I")
        # Không có Mục nào bị nhầm từ "Mục đích", "Mục tiêu"
        self.assertEqual(len(doc.sections), 0)

    def test_08_articles_before_and_after_chapter_transition(self):
        """Kiểm thử các Điều luật trước và sau khi chuyển đổi Chương."""
        text_transition = (
            "Chương I\n"
            "NHỮNG QUY ĐỊNH CHUNG\n\n"
            "Điều 1. Phạm vi\n"
            "Nội dung 1\n\n"
            "Điều 2. Đối tượng\n"
            "Nội dung 2\n\n"
            "Chương II\n"
            "VIỆC LÀM VÀ TUYỂN DỤNG\n\n"
            "Điều 3. Việc làm\n"
            "Nội dung 3\n\n"
            "Điều 4. Tuyển dụng\n"
            "Nội dung 4"
        )
        doc = self.parser.parse(text_transition)
        self.assertEqual(len(doc.chapters), 2)
        self.assertEqual(len(doc.articles), 4)

        # Điều 1 và Điều 2 thuộc Chương I
        self.assertEqual(doc.articles[0].chapter_number, "Chương I")
        self.assertEqual(doc.articles[1].chapter_number, "Chương I")

        # Điều 3 và Điều 4 thuộc Chương II
        self.assertEqual(doc.articles[2].chapter_number, "Chương II")
        self.assertEqual(doc.articles[3].chapter_number, "Chương II")

    def test_09_line_wrapped_dieu_heading(self):
        """Kiểm thử xử lý trường hợp chữ 'Điều' ở dòng 1 và số điều '22. Tiêu đề' ở dòng 2 do ngắt dòng crawler."""
        text_wrapped_dieu = (
            "Chương III\n"
            "QUẢN LÝ LAO ĐỘNG\n\n"
            "Điều\n"
            "22. Thẩm quyền tuyển dụng người lao động nước ngoài\n"
            "1. Doanh nghiệp có thẩm quyền...\n\n"
            "Điều 23. Hồ sơ đề nghị\n"
            "Hồ sơ gồm có..."
        )
        doc = self.parser.parse(text_wrapped_dieu)
        self.assertEqual(len(doc.articles), 2)
        self.assertEqual(doc.articles[0].number, "Điều 22")
        self.assertEqual(doc.articles[0].title, "Thẩm quyền tuyển dụng người lao động nước ngoài")
        self.assertEqual(doc.articles[0].chapter_number, "Chương III")

        self.assertEqual(doc.articles[1].number, "Điều 23")
        self.assertEqual(doc.articles[1].title, "Hồ sơ đề nghị")

    def test_10_no_text_loss(self):
        """Kiểm thử tính toàn vẹn: Không làm mất bất kỳ ký tự nào của nội dung điều luật."""
        sample_body = (
            "1. Người lao động có các quyền sau đây:\n"
            "a) Làm việc, tự do lựa chọn việc làm, nơi làm việc;\n"
            "b) Hưởng lương phù hợp với trình độ, kỹ năng nghề trên cơ sở thỏa thuận;\n"
            "c) Từ chối làm việc nếu có nguy cơ rõ ràng đe dọa trực tiếp đến tính mạng, sức khỏe."
        )
        full_text = (
            "Chương I\n"
            "QUY ĐỊNH CHUNG\n\n"
            "Điều 5. Quyền của người lao động\n"
            f"{sample_body}"
        )
        doc = self.parser.parse(full_text)
        self.assertEqual(len(doc.articles), 1)
        # Toàn bộ các dòng của sample_body phải xuất hiện trong raw_text của Điều 5
        for line in sample_body.split('\n'):
            self.assertIn(line.strip(), doc.articles[0].raw_text)


    def test_11_real_blld_2019_corpus_integration(self):
        """Kiểm thử tích hợp trên văn bản thật BLLD_2019:
        1. BLLD 2019 có đúng 17 Chương.
        2. Điều 1 đến Điều 8 thuộc Chương I (NHỮNG QUY ĐỊNH CHUNG).
        3. Không bị nhảy nhầm sang Chương XI ở Điều 3 đến Điều 8.
        5. Toàn bộ 220 Điều luật thực tế của BLLD 2019 được bóc tách chuẩn xác (loại bỏ 7 citation nhầm lẫn).
        """
        import os
        blld_path = r"D:\Filehoc\KLCN\agentic-rag\Data_Processing\data_corpus_raw\BLLD_2019.txt"
        if not os.path.exists(blld_path):
            self.skipTest("BLLD_2019.txt không tồn tại")

        with open(blld_path, "r", encoding="utf-8") as f:
            text = f.read()

        doc = self.parser.parse(text, document_id="BLLD_2019")
        self.assertEqual(len(doc.chapters), 17)
        self.assertEqual(len(doc.sections), 24)
        self.assertEqual(len(doc.articles), 220)

        # Kiểm tra Điều 1 đến Điều 8 đều thuộc Chương I
        for i in range(1, 9):
            art = next((a for a in doc.articles if a.number == f"Điều {i}"), None)
            self.assertIsNotNone(art, f"Không tìm thấy Điều {i}")
            self.assertEqual(
                art.chapter_number, "Chương I",
                f"Điều {i} bị gán sai chương: {art.chapter_number} (mong đợi: Chương I)"
            )
            self.assertEqual(
                art.chapter_title, "NHỮNG QUY ĐỊNH CHUNG",
                f"Tiêu đề chương Điều {i} bị sai: {art.chapter_title}"
            )

        # Kiểm tra Điều 9 thuộc Chương II
        art9 = next((a for a in doc.articles if a.number == "Điều 9"), None)
        self.assertIsNotNone(art9)
        self.assertEqual(art9.chapter_number, "Chương II")

        # Kiểm tra text tham chiếu trong Điều 3 không bị mất
        art3 = next(a for a in doc.articles if a.number == "Điều 3")
        self.assertIn("Chương XI của Bộ luật này", art3.raw_text)


if __name__ == "__main__":
    unittest.main()
