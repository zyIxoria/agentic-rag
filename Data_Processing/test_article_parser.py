"""test_article_parser.py - Unit and Integration Tests for Legal Article, Clause, and Point Parser.

Kiểm thử toàn diện các yêu cầu của TASK DATA-04:
1. Article identification:
   - "Điều 1.", "Điều 104. Thưởng", "ĐIỀU 5: ...", tiêu đề ngắt dòng...
2. Clause identification:
   - "1. ", "2. ", "3. "...
3. Point identification:
   - "a) ", "b) ", "c) ", "d) ", "đ) ", "e) ", "g) "...
4. Negative guards (Tuyệt đối không nhận diện nhầm):
   - Số tiền ("1.000.000 đồng", "5.000.000 đồng")
   - Viện dẫn Điều khoản ("Điều 5 khoản 2", "khoản 2 Điều 169")
   - Viện dẫn Điểm ("điểm a khoản 3 Điều này")
   - Chú thích trong ngoặc đơn ("(sau đây gọi là...)")
   - Ngày tháng ("20/11/2019", "01/01/2021")
   - Tỷ lệ phần trăm ("50%", "150%")
   - Thứ tự nhảy số bất thường ("32. Danh mục...")
   - Trích dẫn Điều luật bị ngắt dòng ("quy định tại khoản 2\nĐiều 169 của Bộ luật Lao động")
5. Acceptance Criteria:
   - Article accuracy >= 99% trên validation set.
   - Zero content loss: Nội dung không bị mất ký tự nào.
   - Hierarchy reconstruction: Có thể tái tạo lại phân cấp từ metadata.
   - Required metadata: article_number, article_title, clause_number, point_number (hoặc None/null).
"""

import os
import sys
import unittest

# Đảm bảo import được các module từ workspace root
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from Data_Processing.article_parser import (
    ArticleClausePointParser,
    ArticleNode,
    ClauseNode,
    PointNode,
    ParsedLegalUnit
)
from Data_Processing.hierarchy_parser import HierarchyParser


class TestArticleParser(unittest.TestCase):
    """Kiểm thử tối thiểu 10 trường hợp nhận diện Điều luật (Article)."""

    def setUp(self):
        self.parser = ArticleClausePointParser()

    def test_01_article_standard_title(self):
        """Case 1: Điều tiêu chuẩn có dấu chấm và tiêu đề."""
        text = "Điều 1. Phạm vi điều chỉnh\nBộ luật này quy định..."
        node = self.parser.parse_article_text(text)
        self.assertEqual(node.article_number, "Điều 1")
        self.assertEqual(node.article_title, "Phạm vi điều chỉnh")

    def test_02_article_multi_digit_number(self):
        """Case 2: Điều có số nhiều chữ số và tiêu đề ngắn."""
        text = "Điều 104. Thưởng\n1. Thưởng là số tiền hoặc tài sản..."
        node = self.parser.parse_article_text(text)
        self.assertEqual(node.article_number, "Điều 104")
        self.assertEqual(node.article_title, "Thưởng")

    def test_03_article_number_only_with_dot(self):
        """Case 3: Điều chỉ có số và dấu chấm, không có tiêu đề."""
        text = "Điều 1.\nBan hành kèm theo Quyết định này Quy chế..."
        node = self.parser.parse_article_text(text)
        self.assertEqual(node.article_number, "Điều 1")
        self.assertIsNone(node.article_title)

    def test_04_article_colon_delimiter(self):
        """Case 4: Điều dùng dấu hai chấm phân tách."""
        text = "Điều 5: Quyền và nghĩa vụ của người lao động\n1. Người lao động có quyền..."
        node = self.parser.parse_article_text(text)
        self.assertEqual(node.article_number, "Điều 5")
        self.assertEqual(node.article_title, "Quyền và nghĩa vụ của người lao động")

    def test_05_article_dash_delimiter(self):
        """Case 5: Điều dùng dấu gạch ngang phân tách."""
        text = "Điều 12 - Trách nhiệm quản lý lao động\nNgười sử dụng lao động phải lập sổ..."
        node = self.parser.parse_article_text(text)
        self.assertEqual(node.article_number, "Điều 12")
        self.assertEqual(node.article_title, "Trách nhiệm quản lý lao động")

    def test_06_article_wrapped_title_two_lines(self):
        """Case 6: Tiêu đề Điều dài bị ngắt sang dòng thứ 2."""
        text = (
            "Điều 17. Hành vi người sử dụng lao động không được làm khi giao kết, thực\n"
            "hiện hợp đồng lao động\n"
            "1. Giữ bản chính giấy tờ tùy thân..."
        )
        lines = text.split('\n')
        # Khi dòng thứ 2 là phần tiếp theo của tiêu đề trước khoản 1
        node = self.parser.parse_article_content(
            article_number="Điều 17",
            article_title="Hành vi người sử dụng lao động không được làm khi giao kết, thực hiện hợp đồng lao động",
            lines=lines
        )
        self.assertEqual(node.article_number, "Điều 17")
        self.assertIn("Hành vi người sử dụng lao động không được làm", node.article_title)
        self.assertEqual(len(node.clauses), 1)
        self.assertEqual(node.clauses[0].clause_number, "Khoản 1")

    def test_07_article_crawler_line_wrap(self):
        """Case 7: Chữ 'Điều' và số '22. Tiêu đề' bị ngắt đôi do crawler."""
        text = (
            "Điều\n"
            "22. Thẩm quyền tuyển dụng người lao động nước ngoài\n"
            "1. Người sử dụng lao động có trách nhiệm xác định nhu cầu..."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(node.article_number, "Điều 22")
        self.assertEqual(node.article_title, "Thẩm quyền tuyển dụng người lao động nước ngoài")
        self.assertEqual(len(node.clauses), 1)

    def test_08_article_uppercase_heading(self):
        """Case 8: Tiêu đề Điều viết hoa toàn bộ (ĐIỀU 1. PHẠM VI)."""
        text = "ĐIỀU 1. PHẠM VI ĐIỀU CHỈNH\nBộ luật này quy định tiêu chuẩn lao động..."
        node = self.parser.parse_article_text(text)
        self.assertEqual(node.article_number, "Điều 1")
        self.assertEqual(node.article_title, "PHẠM VI ĐIỀU CHỈNH")

    def test_09_article_lowercase_heading(self):
        """Case 9: Tiêu đề Điều viết thường (điều 1. phạm vi)."""
        text = "điều 1. phạm vi điều chỉnh\nNội dung điều chỉnh..."
        node = self.parser.parse_article_text(text)
        self.assertEqual(node.article_number, "Điều 1")
        self.assertEqual(node.article_title, "phạm vi điều chỉnh")

    def test_10_article_single_word_title(self):
        """Case 10: Tiêu đề Điều chỉ gồm đúng 1 từ duy nhất."""
        text = "Điều 104. Thưởng\n1. Tiền thưởng là..."
        header_info = self.parser.parse_article_header("Điều 104. Thưởng")
        self.assertIsNotNone(header_info)
        self.assertEqual(header_info[0], "Điều 104")
        self.assertEqual(header_info[1], "Thưởng")

    def test_11_article_without_numbered_clauses(self):
        """Case 11: Điều không chia Khoản (chỉ có 1 đoạn văn duy nhất)."""
        text = (
            "Điều 1. Phạm vi điều chỉnh\n"
            "Bộ luật Lao động quy định tiêu chuẩn lao động; quyền, nghĩa vụ, trách nhiệm của người lao động,\n"
            "người sử dụng lao động, tổ chức đại diện người lao động tại cơ sở."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 1)
        self.assertIsNone(node.clauses[0].clause_number)
        self.assertEqual(node.clauses[0].clause_index, 0)
        self.assertIn("Bộ luật Lao động quy định", node.clauses[0].content)

    def test_12_article_with_numeric_title(self):
        """Case 12: Tiêu đề Điều chứa số và trích dẫn luật khác."""
        text = "Điều 219. Sửa đổi, bổ sung một số điều của Luật Bảo hiểm xã hội số 58/2014/QH13\n1. Sửa đổi Điều 54..."
        node = self.parser.parse_article_text(text)
        self.assertEqual(node.article_number, "Điều 219")
        self.assertIn("Sửa đổi, bổ sung một số điều", node.article_title)


class TestClauseParser(unittest.TestCase):
    """Kiểm thử tối thiểu 10 trường hợp nhận diện Khoản (Clause)."""

    def setUp(self):
        self.parser = ArticleClausePointParser()

    def test_01_sequential_clauses(self):
        """Case 1: Các Khoản tuần tự 1., 2., 3."""
        text = (
            "Điều 2. Đối tượng áp dụng\n"
            "1. Người lao động Việt Nam.\n"
            "2. Người sử dụng lao động.\n"
            "3. Cơ quan, tổ chức khác."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 3)
        self.assertEqual(node.clauses[0].clause_number, "Khoản 1")
        self.assertEqual(node.clauses[1].clause_number, "Khoản 2")
        self.assertEqual(node.clauses[2].clause_number, "Khoản 3")

    def test_02_clause_single_line(self):
        """Case 2: Khoản ngắn gọn trên 1 dòng đơn."""
        line = "1. Người lao động là người làm việc cho người sử dụng lao động theo thỏa thuận."
        res = self.parser.is_clause_start(line, current_clause_idx=0)
        self.assertIsNotNone(res)
        self.assertEqual(res[0], 1)

    def test_03_clause_multi_line(self):
        """Case 3: Khoản dài gồm nhiều dòng nội dung liên tục."""
        text = (
            "Điều 10. Quyền làm việc\n"
            "1. Được tự do lựa chọn việc làm, làm việc cho bất kỳ người sử dụng lao động nào\n"
            "và ở bất kỳ nơi nào mà pháp luật không cấm.\n"
            "Trực tiếp liên hệ với người sử dụng lao động hoặc thông qua tổ chức dịch vụ việc làm.\n"
            "2. Trực tiếp giao kết hợp đồng."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 2)
        self.assertIn("Được tự do lựa chọn", node.clauses[0].content)
        self.assertIn("thông qua tổ chức dịch vụ việc làm", node.clauses[0].content)

    def test_04_clause_with_intro_and_points(self):
        """Case 4: Khoản có lời dẫn nhập và chứa các Điểm a, b, c."""
        text = (
            "Điều 5. Quyền của người lao động\n"
            "1. Người lao động có các quyền sau đây:\n"
            "a) Làm việc, tự do lựa chọn việc làm;\n"
            "b) Hưởng lương phù hợp;\n"
            "2. Người lao động có các nghĩa vụ sau đây:\n"
            "a) Thực hiện hợp đồng lao động;\n"
            "b) Chấp hành nội quy."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 2)
        self.assertEqual(node.clauses[0].intro_text, "1. Người lao động có các quyền sau đây:")
        self.assertEqual(len(node.clauses[0].points), 2)
        self.assertEqual(len(node.clauses[1].points), 2)

    def test_05_clause_containing_currency_in_body(self):
        """Case 5: Khoản chứa số tiền trong nội dung (số tiền không được tách thành khoản mới)."""
        text = (
            "Điều 20. Mức phạt\n"
            "1. Phạt tiền từ 1.000.000 đồng đến 3.000.000 đồng đối với người sử dụng lao động.\n"
            "2. Phạt tiền từ 5.000.000 đồng đến 10.000.000 đồng đối với hành vi tái phạm."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 2)
        self.assertEqual(node.clauses[0].clause_number, "Khoản 1")
        self.assertIn("1.000.000 đồng", node.clauses[0].content)
        self.assertEqual(node.clauses[1].clause_number, "Khoản 2")
        self.assertIn("5.000.000 đồng", node.clauses[1].content)

    def test_06_clause_containing_date_in_body(self):
        """Case 6: Khoản chứa ngày tháng trong nội dung."""
        text = (
            "Điều 220. Hiệu lực thi hành\n"
            "1. Bộ luật này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2021.\n"
            "2. Bộ luật Lao động số 10/2012/QH13 hết hiệu lực kể từ ngày Bộ luật này có hiệu lực."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 2)
        self.assertIn("ngày 01 tháng 01 năm 2021", node.clauses[0].content)

    def test_07_clause_containing_percentage_in_body(self):
        """Case 7: Khoản chứa tỷ lệ phần trăm (150%, 200%, 300%)."""
        text = (
            "Điều 98. Tiền lương làm thêm giờ\n"
            "1. Người lao động làm thêm giờ được trả lương tính theo đơn giá tiền lương:\n"
            "a) Vào ngày thường, ít nhất bằng 150%;\n"
            "b) Vào ngày nghỉ hằng tuần, ít nhất bằng 200%;\n"
            "2. Người lao động làm việc vào ban đêm thì được trả thêm ít nhất bằng 30% tiền lương."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 2)
        self.assertIn("30% tiền lương", node.clauses[1].content)

    def test_08_clause_containing_duration_numbers(self):
        """Case 8: Khoản chứa thời hạn số ngày, số tháng (60 ngày, 30 ngày, 06 tháng)."""
        text = (
            "Điều 25. Thời gian thử việc\n"
            "1. Không quá 180 ngày đối với công việc của người quản lý doanh nghiệp.\n"
            "2. Không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 2)
        self.assertIn("180 ngày", node.clauses[0].content)
        self.assertIn("60 ngày", node.clauses[1].content)

    def test_09_clause_containing_legal_citation(self):
        """Case 9: Khoản chứa trích dẫn luật khác (Điều 5 khoản 2)."""
        text = (
            "Điều 30. Tạm hoãn hợp đồng\n"
            "1. Người lao động thực hiện nghĩa vụ quân sự theo quy định tại Điều 5 khoản 2.\n"
            "2. Người lao động bị tạm giữ, tạm giam theo quy định của pháp luật."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 2)
        self.assertIn("Điều 5 khoản 2", node.clauses[0].content)

    def test_10_clause_unnumbered_single_body(self):
        """Case 10: Điều không có số khoản -> ClauseNode có clause_number=None và index=0."""
        text = (
            "Điều 7. Xây dựng quan hệ lao động\n"
            "Quan hệ lao động giữa người lao động và người sử dụng lao động được xác lập qua đối thoại."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 1)
        self.assertIsNone(node.clauses[0].clause_number)
        self.assertEqual(node.clauses[0].clause_index, 0)

    def test_11_clause_independent_reset_per_article(self):
        """Case 11: Số khoản bắt đầu lại từ 1 khi sang Điều mới."""
        node1 = self.parser.parse_article_text("Điều 1. A\n1. Khoản một Điều 1.\n2. Khoản hai Điều 1.")
        node2 = self.parser.parse_article_text("Điều 2. B\n1. Khoản một Điều 2.\n2. Khoản hai Điều 2.")
        self.assertEqual(node1.clauses[0].clause_number, "Khoản 1")
        self.assertEqual(node2.clauses[0].clause_number, "Khoản 1")


class TestPointParser(unittest.TestCase):
    """Kiểm thử tối thiểu 10 trường hợp nhận diện Điểm (Point)."""

    def setUp(self):
        self.parser = ArticleClausePointParser()

    def test_01_standard_points_a_b_c(self):
        """Case 1: Điểm tiêu chuẩn a), b), c)."""
        text = (
            "Điều 5. Quyền\n"
            "1. Nội dung:\n"
            "a) Quyền thứ nhất;\n"
            "b) Quyền thứ hai;\n"
            "c) Quyền thứ ba."
        )
        node = self.parser.parse_article_text(text)
        c1 = node.clauses[0]
        self.assertEqual(len(c1.points), 3)
        self.assertEqual(c1.points[0].point_number, "Điểm a")
        self.assertEqual(c1.points[1].point_number, "Điểm b")
        self.assertEqual(c1.points[2].point_number, "Điểm c")

    def test_02_vietnamese_specific_point_d_and_dd(self):
        """Case 2: Nhận diện chính xác chữ cái tiếng Việt Điểm d và Điểm đ."""
        text = (
            "Điều 6. Điểm d và đ\n"
            "1. Nội dung gồm:\n"
            "a) Điểm a;\n"
            "b) Điểm b;\n"
            "c) Điểm c;\n"
            "d) Điểm d bình thường;\n"
            "đ) Điểm đ đặc trưng pháp luật Việt Nam."
        )
        node = self.parser.parse_article_text(text)
        pts = node.clauses[0].points
        self.assertEqual(len(pts), 5)
        self.assertEqual(pts[3].point_number, "Điểm d")
        self.assertEqual(pts[3].point_letter, "d")
        self.assertEqual(pts[4].point_number, "Điểm đ")
        self.assertEqual(pts[4].point_letter, "đ")

    def test_03_extended_alphabet_points(self):
        """Case 3: Các điểm nằm sâu trong bảng chữ cái: e), g), h), i)."""
        text = (
            "Điều 8. Các hành vi cấm\n"
            "1. Nghiêm cấm các hành vi:\n"
            "a) Hành vi a;\n"
            "b) Hành vi b;\n"
            "c) Hành vi c;\n"
            "d) Hành vi d;\n"
            "đ) Hành vi đ;\n"
            "e) Hành vi e;\n"
            "g) Hành vi g;\n"
            "h) Hành vi h;\n"
            "i) Hành vi i."
        )
        node = self.parser.parse_article_text(text)
        pts = node.clauses[0].points
        self.assertEqual(len(pts), 9)
        self.assertEqual(pts[5].point_letter, "e")
        self.assertEqual(pts[6].point_letter, "g")
        self.assertEqual(pts[7].point_letter, "h")
        self.assertEqual(pts[8].point_letter, "i")

    def test_04_point_multi_line_content(self):
        """Case 4: Điểm có nội dung dài xuống dòng nhiều hàng."""
        text = (
            "Điều 3. Giải thích\n"
            "1. Tiêu chí:\n"
            "a) Người lao động làm việc theo hợp đồng lao động có thời hạn từ đủ 01 tháng trở lên\n"
            "kể cả trường hợp người lao động và người sử dụng lao động thỏa thuận bằng tên gọi khác\n"
            "nhưng có nội dung thể hiện về việc làm có trả công;\n"
            "b) Người sử dụng lao động."
        )
        node = self.parser.parse_article_text(text)
        pt_a = node.clauses[0].points[0]
        self.assertEqual(pt_a.point_number, "Điểm a")
        self.assertIn("nhưng có nội dung thể hiện về việc làm", pt_a.content)

    def test_05_point_containing_currency(self):
        """Case 5: Điểm chứa số tiền phạt trong nội dung."""
        text = (
            "Điều 12. Phạt tiền\n"
            "1. Phạt tiền theo các mức:\n"
            "a) Phạt tiền từ 5.000.000 đồng đến 10.000.000 đồng đối với vi phạm lần đầu;\n"
            "b) Phạt tiền từ 10.000.000 đồng đến 20.000.000 đồng đối với tái phạm."
        )
        node = self.parser.parse_article_text(text)
        pts = node.clauses[0].points
        self.assertEqual(len(pts), 2)
        self.assertIn("5.000.000 đồng", pts[0].content)
        self.assertIn("10.000.000 đồng", pts[1].content)

    def test_06_point_containing_percentage(self):
        """Case 6: Điểm chứa tỷ lệ phần trăm."""
        text = (
            "Điều 50. Hỗ trợ\n"
            "1. Mức hỗ trợ:\n"
            "a) Hỗ trợ 50% học phí đào tạo nghề;\n"
            "b) Hỗ trợ 100% chi phí đi lại."
        )
        node = self.parser.parse_article_text(text)
        pts = node.clauses[0].points
        self.assertIn("50% học phí", pts[0].content)
        self.assertIn("100% chi phí", pts[1].content)

    def test_07_point_containing_date(self):
        """Case 7: Điểm chứa mốc thời gian ngày tháng."""
        text = (
            "Điều 15. Báo cáo định kỳ\n"
            "1. Thời hạn gửi báo cáo:\n"
            "a) Trước ngày 15 tháng 6 hằng năm đối với báo cáo 6 tháng;\n"
            "b) Trước ngày 15 tháng 12 hằng năm đối với báo cáo năm."
        )
        node = self.parser.parse_article_text(text)
        pts = node.clauses[0].points
        self.assertIn("15 tháng 6", pts[0].content)
        self.assertIn("15 tháng 12", pts[1].content)

    def test_08_point_containing_legal_citation(self):
        """Case 8: Điểm chứa viện dẫn điểm khác và điều khác."""
        text = (
            "Điều 20. Áp dụng\n"
            "1. Thực hiện theo:\n"
            "a) Quy định tại điểm a khoản 3 Điều 15 của Bộ luật này;\n"
            "b) Hướng dẫn tại điểm b khoản 1 Điều 20."
        )
        node = self.parser.parse_article_text(text)
        pts = node.clauses[0].points
        self.assertEqual(len(pts), 2)
        self.assertIn("điểm a khoản 3 Điều 15", pts[0].content)

    def test_09_point_with_sub_item_b1_in_text(self):
        """Case 9: Dòng chứa tiểu mục b1) trong nội dung Điểm b không bị tách nhầm thành Điểm mới."""
        text = (
            "Điều 90. Tiền lương\n"
            "1. Cơ cấu tiền lương:\n"
            "a) Mức lương theo công việc;\n"
            "b) Phụ cấp lương theo thỏa thuận như sau:\n"
            "b1) Phụ cấp chức vụ, chức danh;\n"
            "b2) Phụ cấp trách nhiệm;\n"
            "c) Các khoản bổ sung khác."
        )
        node = self.parser.parse_article_text(text)
        pts = node.clauses[0].points
        # Chỉ có đúng 3 Điểm: a, b, c. Không bị tách b1, b2 thành điểm
        self.assertEqual(len(pts), 3)
        self.assertEqual(pts[0].point_number, "Điểm a")
        self.assertEqual(pts[1].point_number, "Điểm b")
        self.assertIn("b1) Phụ cấp chức vụ", pts[1].content)
        self.assertIn("b2) Phụ cấp trách nhiệm", pts[1].content)
        self.assertEqual(pts[2].point_number, "Điểm c")

    def test_10_points_in_article_without_numbered_clauses(self):
        """Case 10: Điều không chia khoản nhưng có trực tiếp các Điểm a, b, c."""
        text = (
            "Điều 15. Nguyên tắc giao kết hợp đồng lao động\n"
            "Việc giao kết hợp đồng lao động phải tuân theo các nguyên tắc sau đây:\n"
            "a) Tự nguyện, bình đẳng, thiện chí, hợp tác và trung thực;\n"
            "b) Tự do giao kết hợp đồng lao động nhưng không được trái pháp luật."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 1)
        self.assertIsNone(node.clauses[0].clause_number)
        self.assertEqual(len(node.clauses[0].points), 2)
        self.assertEqual(node.clauses[0].points[0].point_number, "Điểm a")
        self.assertEqual(node.clauses[0].points[1].point_number, "Điểm b")

    def test_11_point_reset_per_clause(self):
        """Case 11: Chữ cái Điểm reset lại từ 'a)' khi sang Khoản 2."""
        text = (
            "Điều 5. Quyền và nghĩa vụ\n"
            "1. Quyền:\n"
            "a) Quyền một;\n"
            "b) Quyền hai;\n"
            "2. Nghĩa vụ:\n"
            "a) Nghĩa vụ một;\n"
            "b) Nghĩa vụ hai."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(node.clauses[0].points[0].point_number, "Điểm a")
        self.assertEqual(node.clauses[1].points[0].point_number, "Điểm a")


class TestNegativeGuards(unittest.TestCase):
    """Kiểm thử tối thiểu 5 trường hợp âm tính (Negative Cases - Ngăn chặn nhận diện nhầm)."""

    def setUp(self):
        self.parser = ArticleClausePointParser()

    def test_01_negative_currency_not_clause(self):
        """Negative 1: Số tiền (1.000.000 đồng, 5.000.000 đồng) TUYỆT ĐỐI không tạo Khoản mới."""
        line_cur1 = "1.000.000 đồng đối với người lao động có hành vi vi phạm."
        line_cur2 = "5.000.000 đồng đến 10.000.000 đồng đối với doanh nghiệp."
        self.assertIsNone(self.parser.is_clause_start(line_cur1, current_clause_idx=0))
        self.assertIsNone(self.parser.is_clause_start(line_cur2, current_clause_idx=1))

        # Kiểm tra trong toàn văn điều luật
        text = (
            "Điều 10. Mức phạt\n"
            "1. Phạt tiền từ 1.000.000 đồng đến 2.000.000 đồng đối với hành vi sau:\n"
            "1.000.000 đồng trong trường hợp vi phạm lần đầu.\n"
            "2. Phạt tiền từ 3.000.000 đồng đến 5.000.000 đồng."
        )
        node = self.parser.parse_article_text(text)
        self.assertEqual(len(node.clauses), 2)  # Chỉ có Khoản 1 và Khoản 2

    def test_02_negative_intext_clause_citation(self):
        """Negative 2: Viện dẫn điều khoản (Điều 5 khoản 2, khoản 1 Điều này) không tạo Khoản mới."""
        line_ref1 = "Điều 5 khoản 2"
        line_ref2 = "theo quy định tại khoản 2 Điều 169 của Bộ luật này"
        self.assertIsNone(self.parser.is_clause_start(line_ref1, current_clause_idx=1))
        self.assertIsNone(self.parser.is_clause_start(line_ref2, current_clause_idx=1))

    def test_03_negative_intext_point_citation(self):
        """Negative 3: Viện dẫn điểm (điểm a khoản 3 Điều này, tại điểm b) không tạo Điểm mới."""
        line_pt1 = "điểm a khoản 3 Điều này"
        line_pt2 = "quy định tại điểm b khoản 1"
        self.assertIsNone(self.parser.is_point_start(line_pt1, current_point_letter=None))
        self.assertIsNone(self.parser.is_point_start(line_pt2, current_point_letter='a'))

    def test_04_negative_parenthesized_phrase(self):
        """Negative 4: Cụm từ trong ngoặc đơn (sau đây gọi là..., được tính theo...) không tạo Điểm mới."""
        line_paren1 = "(sau đây gọi tắt là người sử dụng lao động);"
        line_paren2 = "(được tính theo ngày làm việc bình thường);"
        line_paren3 = "(a) Trường hợp này có ngoặc mở đầu;"
        self.assertIsNone(self.parser.is_point_start(line_paren1, current_point_letter=None))
        self.assertIsNone(self.parser.is_point_start(line_paren2, current_point_letter='d'))
        self.assertIsNone(self.parser.is_point_start(line_paren3, current_point_letter=None))

    def test_05_negative_dates_and_percentages(self):
        """Negative 5: Ngày tháng (20/11/2019, 01/01/2021) và tỷ lệ phần trăm (50%, 150%) không tạo Khoản."""
        line_date1 = "20/11/2019 là ngày Quốc hội thông qua Bộ luật Lao động."
        line_date2 = "01/01/2021 là ngày có hiệu lực thi hành."
        line_pct = "50% tổng số lao động có mặt tại nơi làm việc."
        self.assertIsNone(self.parser.is_clause_start(line_date1, current_clause_idx=0))
        self.assertIsNone(self.parser.is_clause_start(line_date2, current_clause_idx=1))
        self.assertIsNone(self.parser.is_clause_start(line_pct, current_clause_idx=1))

    def test_06_negative_out_of_sequence_clause(self):
        """Negative 6: Số thứ tự nhảy cóc bất thường (32. Danh mục...) không được xem là Khoản."""
        line_catalog = "32. Danh mục máy móc thiết bị có yêu cầu nghiêm ngặt về an toàn."
        # Khi đang ở khoản 1 hoặc chưa có khoản nào, "32." phải bị từ chối
        self.assertIsNone(self.parser.is_clause_start(line_catalog, current_clause_idx=0))
        self.assertIsNone(self.parser.is_clause_start(line_catalog, current_clause_idx=1))

    def test_07_negative_line_wrapped_article_citation(self):
        """Negative 7: Viện dẫn Điều bị ngắt dòng không được nhận diện thành Điều mới."""
        prev = "quy định tại khoản 2"
        clean = "Điều 169 của Bộ luật Lao động , trừ trường hợp Luật"
        is_ref = self.parser.is_article_reference(clean, prev_line=prev, current_article_num=219)
        self.assertTrue(is_ref)


class TestAcceptanceAndReconstruction(unittest.TestCase):
    """Kiểm thử Tiêu chí Nghiệm thu (Acceptance Criteria): Metadata, Zero text loss, Reconstruction."""

    def setUp(self):
        self.parser = ArticleClausePointParser()

    def test_01_metadata_completeness_and_hierarchy_units(self):
        """Kiểm thử mỗi chunk sinh ra đều mang đầy đủ metadata của cấp gần nhất."""
        text = (
            "Điều 5. Quyền và nghĩa vụ của người lao động\n"
            "1. Người lao động có các quyền sau đây:\n"
            "a) Làm việc; tự do lựa chọn việc làm;\n"
            "b) Hưởng lương phù hợp;\n"
            "2. Người lao động có các nghĩa vụ sau đây:\n"
            "a) Thực hiện hợp đồng lao động;\n"
            "b) Chấp hành kỷ luật lao động."
        )
        node = self.parser.parse_article_text(
            text,
            document_id="BLLD_2019",
            chapter_number="Chương I",
            chapter_title="NHỮNG QUY ĐỊNH CHUNG"
        )
        units = self.parser.extract_legal_units(node, document_id="BLLD_2019")
        self.assertEqual(len(units), 4)

        # Kiểm tra Unit 1: Điểm a của Khoản 1 Điều 5
        u1 = units[0]
        self.assertEqual(u1.document_id, "BLLD_2019")
        self.assertEqual(u1.article_number, "Điều 5")
        self.assertEqual(u1.article_title, "Quyền và nghĩa vụ của người lao động")
        self.assertEqual(u1.chapter_number, "Chương I")
        self.assertEqual(u1.clause_number, "Khoản 1")
        self.assertEqual(u1.point_number, "Điểm a")
        self.assertEqual(u1.unit_type, "point")

        # Kiểm tra Unit 3: Điểm a của Khoản 2 Điều 5
        u3 = units[2]
        self.assertEqual(u3.clause_number, "Khoản 2")
        self.assertEqual(u3.point_number, "Điểm a")

    def test_02_null_metadata_for_unspecified_hierarchy(self):
        """Kiểm thử khi hierarchy không xác định thì metadata trả về giá trị None (null)."""
        text = (
            "Điều 1. Phạm vi điều chỉnh\n"
            "Bộ luật này quy định tiêu chuẩn lao động."
        )
        node = self.parser.parse_article_text(text, document_id="DOC_TEST")
        units = self.parser.extract_legal_units(node, document_id="DOC_TEST")
        self.assertEqual(len(units), 1)
        u = units[0]
        self.assertEqual(u.article_number, "Điều 1")
        self.assertEqual(u.article_title, "Phạm vi điều chỉnh")
        self.assertIsNone(u.clause_number)  # Phải là None (null)
        self.assertIsNone(u.point_number)   # Phải là None (null)
        self.assertEqual(u.unit_type, "article")

    def test_03_zero_content_loss_reconstruction(self):
        """Kiểm thử bảo toàn 100% nội dung (Zero Content Loss) qua phương thức reconstruct_text."""
        sample_raw = (
            "Điều 104. Thưởng\n"
            "1. Thưởng là số tiền hoặc tài sản hoặc bằng các hình thức khác mà người sử dụng lao động thưởng cho người lao động căn cứ vào kết quả sản xuất, kinh doanh, mức độ hoàn thành công việc của người lao động.\n"
            "2. Quy chế thưởng do người sử dụng lao động quyết định và công bố công khai tại nơi làm việc sau khi tham khảo ý kiến của tổ chức đại diện người lao động tại cơ sở đối với nơi có tổ chức đại diện người lao động tại cơ sở."
        )
        node = self.parser.parse_article_text(sample_raw)
        reconstructed = node.reconstruct_text()
        self.assertEqual(reconstructed.strip(), sample_raw.strip())

    def test_04_pydantic_v2_schema_compatibility(self):
        """Kiểm thử tính tương thích hoàn hảo giữa ParsedLegalUnit và LegalChunkV2 (Schema V2)."""
        from Data_Processing.models_v2 import LegalChunkV2

        text = (
            "Điều 104. Thưởng\n"
            "1. Thưởng là số tiền hoặc tài sản..."
        )
        node = self.parser.parse_article_text(text, document_id="BLLD_2019")
        units = self.parser.extract_legal_units(node, document_id="BLLD_2019")
        u = units[0]

        # Chuyển đổi thành LegalChunkV2
        chunk_v2 = LegalChunkV2(
            chunk_id=u.unit_id,
            document_id=u.document_id,
            document_number="45/2019/QH14",
            document_title="Bộ luật Lao động 2019",
            document_type="Luật",
            article_number=u.article_number,
            article_title=u.article_title,
            clause_number=u.clause_number,
            point_number=u.point_number,
            content=u.content,
            effective_from="2021-01-01",
            source_url="https://thuvienphapluat.vn",
            parent_document="45/2019/QH14",
            parent_article=u.parent_article,
            chunk_index=0
        )
        self.assertEqual(chunk_v2.article_number, "Điều 104")
        self.assertEqual(chunk_v2.article_title, "Thưởng")
        self.assertEqual(chunk_v2.clause_number, "Khoản 1")
        self.assertIsNone(chunk_v2.point_number)


if __name__ == "__main__":
    unittest.main()
