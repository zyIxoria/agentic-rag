# -*- coding: utf-8 -*-
"""
Module chứa các câu hỏi kiểm thử nhóm Từ chối (Refusal):
- insufficient_evidence (17 câu: Q217 - Q233): Thuộc lĩnh vực lao động nhưng thiếu căn cứ trong 19 văn bản
- out_of_scope (17 câu: Q234 - Q250): Nằm hoàn toàn ngoài phạm vi pháp luật lao động
"""

QUESTIONS_INSUFFICIENT_EVIDENCE = [
    {
        "question_id": "Q217",
        "question": "Mức đóng đoàn phí công đoàn hàng tháng của đoàn viên công đoàn làm việc tại doanh nghiệp ngoài nhà nước là bao nhiêu phần trăm tiền lương?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q218",
        "question": "Điều kiện và mức vay vốn hỗ trợ tạo việc làm tối đa từ Quỹ quốc gia về việc làm đối với cơ sở sản xuất kinh doanh là bao nhiêu tiền theo quy định pháp luật?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q219",
        "question": "Mức phụ cấp độc hại, nguy hiểm bằng tiền đối với nhân viên y tế làm việc trong môi trường bức xạ y học được quy định cụ thể là bao nhiêu đồng mỗi tháng?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q220",
        "question": "Thủ tục và hồ sơ xin cấp thẻ tạm trú thời hạn 3 năm cho vợ hoặc chồng của chuyên gia lao động nước ngoài làm việc tại Việt Nam gồm những giấy tờ gì?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q221",
        "question": "Diện tích phòng học lý thuyết tối thiểu của cơ sở giáo dục nghề nghiệp đào tạo nghề lái xe ô tô hạng B2 được quy định là bao nhiêu mét vuông?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q222",
        "question": "Người lao động nông thôn thuộc hộ nghèo tham gia lớp học nghề ngắn hạn dưới 03 tháng được ngân sách nhà nước hỗ trợ tiền ăn bao nhiêu tiền một ngày công?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q223",
        "question": "Mức giảm trừ gia cảnh cho bản thân người nộp thuế và cho mỗi người phụ thuộc khi tính thuế thu nhập cá nhân từ tiền lương hiện nay là bao nhiêu triệu đồng mỗi tháng?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q224",
        "question": "Trình tự kỹ thuật đăng ký và cấp tài khoản khai trình việc sử dụng lao động trực tuyến qua Cổng Dịch vụ công Quốc gia gồm mấy bước thực hiện?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q225",
        "question": "Mức hệ số phụ cấp chức vụ lãnh đạo đối với Trưởng phòng chuyên môn thuộc Ủy ban nhân dân cấp huyện được quy định là hệ số bao nhiêu?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q226",
        "question": "Điều kiện diện tích trụ sở làm việc và vốn điều lệ tối thiểu để thành lập Trung tâm dịch vụ việc làm công lập cấp tỉnh là bao nhiêu?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q227",
        "question": "Thời hạn chuyển giao quyền sở hữu công nghiệp đối với sáng chế do người lao động tạo ra theo nhiệm vụ được giao trong doanh nghiệp là bao nhiêu tháng kể từ khi tạo ra?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q228",
        "question": "Chế độ bồi thường tai nạn lao động đối với thuyền viên làm việc trên tàu biển đăng ký quốc tịch nước ngoài gặp nạn ngoài vùng biển Việt Nam được quy định như thế nào?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q229",
        "question": "Mức thanh toán khoán tiền công tác phí theo ngày đối với người lao động đi công tác nước ngoài tại khu vực Đông Nam Á được quy định là bao nhiêu USD một ngày?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q230",
        "question": "Tiêu chuẩn kỹ thuật và khoảng cách an toàn phòng ngừa độc hại đối với hệ thống kho chứa hóa chất nguy hiểm loại 1 trong nhà xưởng công nghiệp quy định tối thiểu là bao nhiêu mét?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q231",
        "question": "Hồ sơ và thủ tục thành lập Ban chấp hành công đoàn cơ sở lâm thời tại doanh nghiệp mới thành lập gồm những văn bản gì gửi liên đoàn lao động cấp quận/huyện?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q232",
        "question": "Mức trợ cấp bằng tiền khuyến khích tìm việc làm mới cho người lao động bị thu hồi toàn bộ đất sản xuất nông nghiệp được tính theo tỷ lệ cụ thể nào trên giá đất bồi thường?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q233",
        "question": "Tỷ lệ phát hành cổ phiếu thưởng cho người lao động (chương trình ESOP) tối đa của công ty cổ phần niêm yết trên sàn chứng khoán là bao nhiêu phần trăm trên tổng số cổ phần lưu hành?",
        "category": "insufficient_evidence",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    }
]

QUESTIONS_OUT_OF_SCOPE = [
    {
        "question_id": "Q234",
        "question": "Người điều khiển xe mô tô hai bánh đi vào đường cao tốc thì bị xử phạt vi phạm hành chính bao nhiêu tiền và có bị tước giấy phép lái xe không?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q235",
        "question": "Mức hình phạt tù cao nhất đối với tội trộm cắp tài sản theo quy định tại Bộ luật Hình sự Việt Nam là bao nhiêu năm?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q236",
        "question": "Thủ tục công chứng hợp đồng mua bán, chuyển nhượng quyền sử dụng đất và tài sản gắn liền với đất giữa hai cá nhân cần chuẩn bị những giấy tờ gì?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q237",
        "question": "Con riêng của vợ hoặc con riêng của chồng có đương nhiên được hưởng thừa kế theo pháp luật đối với di sản của bố dượng, mẹ kế không?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q238",
        "question": "Mức thu lệ phí trước bạ khi đăng ký quyền sở hữu xe ô tô con chở người từ 9 chỗ ngồi trở xuống lần đầu được tính theo tỷ lệ bao nhiêu phần trăm?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q239",
        "question": "Trong ngôn ngữ lập trình Python, decorator @classmethod khác biệt với @staticmethod như thế nào và trường hợp nào nên dùng mỗi loại?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q240",
        "question": "Thuật toán sắp xếp QuickSort có độ phức tạp thời gian trung bình (average case) và trường hợp xấu nhất (worst case) là bao nhiêu?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q241",
        "question": "Công thức toán học tính diện tích hình cầu bán kính R và thể tích khối cầu tương ứng là gì?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q242",
        "question": "Nguyên nhân vật lý gây ra hiện tượng nhật thực toàn phần và chu kỳ Saros trong thiên văn học kéo dài trong khoảng thời gian bao lâu?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q243",
        "question": "Vitamin C (Acid Ascorbic) có vai trò sinh hóa như thế nào đối với quá trình tổng hợp collagen và tăng cường hệ miễn dịch của cơ thể con người?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q244",
        "question": "Thủ tục đăng ký bảo hộ nhãn hiệu hàng hóa tại Cục Sở hữu trí tuệ Việt Nam mất thời gian thẩm định nội dung theo luật định là bao nhiêu tháng?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q245",
        "question": "Nghĩa vụ quân sự tại Việt Nam áp dụng độ tuổi gọi nhập ngũ từ đủ bao nhiêu tuổi đến hết bao nhiêu tuổi đối với công dân nam đã tốt nghiệp cao đẳng hoặc đại học?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q246",
        "question": "Điều kiện và tiêu chuẩn chuyên môn để một cá nhân được cấp chứng chỉ hành nghề môi giới bất động sản tại Việt Nam là gì?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q247",
        "question": "Khi vợ chồng ly hôn, tài sản được tạo lập trong thời kỳ hôn nhân nhưng giấy tờ sở hữu chỉ đứng tên một bên vợ hoặc chồng thì được phân chia theo nguyên tắc nào?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q248",
        "question": "Hiệp định Đối tác Toàn diện và Tiến bộ xuyên Thái Bình Dương (CPTPP) chính thức có hiệu lực đối với Việt Nam từ ngày tháng năm nào?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q249",
        "question": "Tốc độ tối đa cho phép đối với xe mô tô hai bánh khi tham gia giao thông trong khu vực đông dân cư trên đường đôi hoặc đường một chiều có từ hai làn xe trở lên là bao nhiêu km/h?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    },
    {
        "question_id": "Q250",
        "question": "Trong kiến trúc mạng nơ-ron Transformer, cơ chế Scaled Dot-Product Attention được tính toán theo công thức toán học nào?",
        "category": "out_of_scope",
        "gold_sources": [],
        "reference_answer": "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy.",
        "requires_refusal": True
    }
]

