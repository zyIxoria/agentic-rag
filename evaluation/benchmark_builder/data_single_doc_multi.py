"""Single Document Multi Chunk Questions (Q098 - Q120)."""

QUESTIONS_SINGLE_DOC_MULTI = [
    {
        "question_id": "Q098",
        "question": "Điều kiện về thời gian đóng bảo hiểm xã hội tối thiểu để hưởng lương hưu và cách tính tỷ lệ hưởng lương hưu hằng tháng theo Luật Bảo hiểm xã hội 2024?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 64",
                "chunk_ids": ["LUAT_BHXH_2024_Điều64_Khoản1_P1_143"]
            },
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 66",
                "chunk_ids": ["LUAT_BHXH_2024_Điều66_Khoản1_147"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 64 và Điều 66 Luật Bảo hiểm xã hội 2024: Người lao động khi nghỉ việc có thời gian đóng bảo hiểm xã hội bắt buộc từ đủ 15 năm trở lên và đủ tuổi nghỉ hưu theo quy định thì được hưởng lương hưu hằng tháng. Mức lương hưu hằng tháng bằng tỷ lệ hưởng lương hưu nhân với mức bình quân tiền lương làm căn cứ đóng BHXH. Đối với lao động nữ, đóng đủ 15 năm BHXH tính bằng 45%, sau đó cứ mỗi năm đóng thêm được tính thêm 2%, tối đa 75%. Đối với lao động nam, đóng đủ 15 năm tính bằng 40%, sau đó đóng đủ 20 năm tính bằng 45%, cứ thêm 1 năm tính thêm 2%, tối đa 75%.",
        "requires_refusal": False
    },
    {
        "question_id": "Q099",
        "question": "Lao động nữ sinh con cần đáp ứng điều kiện đóng BHXH như thế nào để được hưởng chế độ thai sản và thời gian nghỉ sinh con tối đa là bao lâu?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 50",
                "chunk_ids": ["LUAT_BHXH_2024_Điều50_Khoản2_111"]
            },
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 53",
                "chunk_ids": ["LUAT_BHXH_2024_Điều53_Khoản1_115"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 50 và Điều 53 Luật Bảo hiểm xã hội 2024: Lao động nữ sinh con phải đóng bảo hiểm xã hội bắt buộc từ đủ 06 tháng trở lên trong thời gian 12 tháng trước khi sinh con (hoặc đóng đủ 12 tháng trở lên mà khi mang thai phải nghỉ việc dưỡng thai theo chỉ định thì phải đóng đủ 03 tháng trở lên trong 12 tháng trước khi sinh). Khi đủ điều kiện, lao động nữ sinh con được nghỉ việc hưởng chế độ thai sản trước và sau khi sinh con là 06 tháng; trường hợp sinh đôi trở lên thì từ con thứ hai trở đi, cứ mỗi con người mẹ được nghỉ thêm 01 tháng.",
        "requires_refusal": False
    },
    {
        "question_id": "Q100",
        "question": "Trường hợp nào người lao động được rút bảo hiểm xã hội một lần và hồ sơ đề nghị hưởng gồm những giấy tờ gì theo Luật Bảo hiểm xã hội 2024?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 70",
                "chunk_ids": ["LUAT_BHXH_2024_Điều70_Khoản1_153"]
            },
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 102",
                "chunk_ids": ["LUAT_BHXH_2024_Điều102_Khoản1_210"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 70 và Điều 102 Luật Bảo hiểm xã hội 2024: Người lao động được rút BHXH một lần khi thuộc các trường hợp: đủ tuổi nghỉ hưu mà chưa đủ 15 năm đóng BHXH và không tiếp tục tham gia; ra nước ngoài để định cư; mắc một trong những bệnh hiểm nghèo như ung thư, bại liệt, xơ gan mất bù... theo quy định; hoặc người có thời gian đóng BHXH trước ngày Luật có hiệu lực mà sau 12 tháng không thuộc diện tham gia BHXH bắt buộc và có yêu cầu. Hồ sơ hưởng gồm: Sổ bảo hiểm xã hội; Đơn đề nghị hưởng bảo hiểm xã hội một lần; cùng các giấy tờ chứng minh trường hợp định cư hoặc tóm tắt hồ sơ bệnh án/giấy xác nhận bệnh tật.",
        "requires_refusal": False
    },
    {
        "question_id": "Q101",
        "question": "Người lao động nghỉ ốm đau trong điều kiện bình thường được nghỉ tối đa bao nhiêu ngày trong một năm và cần đáp ứng điều kiện gì để được hưởng chế độ?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 42",
                "chunk_ids": ["LUAT_BHXH_2024_Điều42_Khoản1_95"]
            },
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 44",
                "chunk_ids": ["LUAT_BHXH_2024_Điều44_Khoản1_99"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 42 và Điều 44 Luật Bảo hiểm xã hội 2024: Người lao động được hưởng chế độ ốm đau khi phải nghỉ việc do bị ốm đau, tai nạn (không phải tai nạn lao động) và có xác nhận của cơ sở khám bệnh, chữa bệnh có thẩm quyền. Thời gian tối đa hưởng chế độ ốm đau trong một năm đối với người làm việc trong điều kiện bình thường: 30 ngày nếu đã đóng BHXH dưới 15 năm; 40 ngày nếu đã đóng từ đủ 15 năm đến dưới 30 năm; và 60 ngày nếu đã đóng từ đủ 30 năm trở lên.",
        "requires_refusal": False
    },
    {
        "question_id": "Q102",
        "question": "Khi người lao động bị tai nạn lao động, người sử dụng lao động có những trách nhiệm sơ cứu, trả lương nào và mức bồi thường tai nạn lao động được xác định ra sao?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "LUAT_ATVSLD_2015",
                "article_number": "Điều 38",
                "chunk_ids": ["LUAT_ATVSLD_2015_Điều38_Khoản1_101", "LUAT_ATVSLD_2015_Điều38_Khoản2_102"]
            },
            {
                "document_id": "LUAT_ATVSLD_2015",
                "article_number": "Điều 39",
                "chunk_ids": ["LUAT_ATVSLD_2015_Điều39_Khoản1_108"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 38 và Điều 39 Luật An toàn, vệ sinh lao động 2015: Người sử dụng lao động có trách nhiệm: kịp thời sơ cứu, cấp cứu; tạm ứng và thanh toán chi phí y tế điều trị; trả đủ tiền lương trong thời gian người lao động điều trị, phục hồi chức năng; và bồi thường tai nạn lao động. Mức bồi thường khi tai nạn không do lỗi của người lao động: ít nhất 1,5 tháng tiền lương nếu suy giảm từ 5% đến 10% khả năng lao động, sau đó cứ tăng 1% được cộng thêm 0,4 tháng tiền lương; ít nhất 30 tháng tiền lương cho người lao động bị suy giảm từ 81% trở lên hoặc cho thân nhân người lao động bị chết do tai nạn lao động.",
        "requires_refusal": False
    },
    {
        "question_id": "Q103",
        "question": "Người sử dụng lao động có trách nhiệm tổ chức huấn luyện an toàn vệ sinh lao động và kiểm định máy móc, thiết bị có yêu cầu nghiêm ngặt như thế nào?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "LUAT_ATVSLD_2015",
                "article_number": "Điều 14",
                "chunk_ids": ["LUAT_ATVSLD_2015_Điều14_Khoản1_37"]
            },
            {
                "document_id": "LUAT_ATVSLD_2015",
                "article_number": "Điều 15",
                "chunk_ids": ["LUAT_ATVSLD_2015_Điều15_43"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 14 và Điều 15 Luật An toàn, vệ sinh lao động 2015: Người sử dụng lao động phải tổ chức huấn luyện an toàn, vệ sinh lao động cho người quản lý, người làm công tác an toàn, người lao động làm công việc có yêu cầu nghiêm ngặt về an toàn, vệ sinh lao động và người làm công tác y tế. Đồng thời, các loại máy, thiết bị, vật tư có yêu cầu nghiêm ngặt về an toàn lao động phải được kiểm định kỹ thuật an toàn trước khi đưa vào sử dụng và kiểm định định kỳ trong quá trình sử dụng bởi tổ chức hoạt động kiểm định hợp pháp.",
        "requires_refusal": False
    },
    {
        "question_id": "Q104",
        "question": "Trách nhiệm của người sử dụng lao động trong việc bảo đảm điều kiện an toàn tại nơi làm việc và quan trắc môi trường lao động được quy định như thế nào?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "LUAT_ATVSLD_2015",
                "article_number": "Điều 16",
                "chunk_ids": ["LUAT_ATVSLD_2015_Điều16_Khoản1_44"]
            },
            {
                "document_id": "LUAT_ATVSLD_2015",
                "article_number": "Điều 18",
                "chunk_ids": ["LUAT_ATVSLD_2015_Điều18_Khoản1_50"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 16 và Điều 18 Luật An toàn, vệ sinh lao động 2015: Người sử dụng lao động phải bảo đảm nơi làm việc đạt yêu cầu về không gian, độ thoáng, độ sáng, tiêu chuẩn vệ sinh lao động; định kỳ kiểm tra, bảo dưỡng máy móc thiết bị; trang bị bảng chỉ dẫn an toàn. Người sử dụng lao động phải tổ chức quan trắc môi trường lao động để đánh giá yếu tố có hại ít nhất một lần trong một năm; lập hồ sơ vệ sinh lao động và công khai kết quả quan trắc cho người lao động được biết.",
        "requires_refusal": False
    },
    {
        "question_id": "Q105",
        "question": "Những đối tượng nào bắt buộc phải tham gia bảo hiểm thất nghiệp và người lao động cần đáp ứng điều kiện gì để được hưởng trợ cấp thất nghiệp?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "LUAT_VIEC_LAM_2013",
                "article_number": "Điều 43",
                "chunk_ids": ["LUAT_VIEC_LAM_2013_Điều43_Khoản1_40"]
            },
            {
                "document_id": "LUAT_VIEC_LAM_2013",
                "article_number": "Điều 49",
                "chunk_ids": ["LUAT_VIEC_LAM_2013_Điều49_Khoản1_47"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 43 và Điều 49 Luật Việc làm 2013: Người lao động làm việc theo hợp đồng lao động không xác định thời hạn hoặc xác định thời hạn từ đủ 03 tháng trở lên bắt buộc phải tham gia bảo hiểm thất nghiệp. Điều kiện hưởng trợ cấp thất nghiệp gồm: 1. Đã chấm dứt hợp đồng lao động đúng quy định (trừ đơn phương chấm dứt trái pháp luật, hưởng lương hưu); 2. Đã đóng BHTN từ đủ 12 tháng trở lên trong thời gian 24 tháng trước khi chấm dứt HĐLĐ; 3. Đã nộp hồ sơ hưởng trợ cấp tại trung tâm dịch vụ việc làm trong 03 tháng kể từ ngày chấm dứt HĐLĐ; 4. Chưa tìm được việc làm sau 15 ngày kể từ ngày nộp hồ sơ.",
        "requires_refusal": False
    },
    {
        "question_id": "Q106",
        "question": "Người lao động đang hưởng trợ cấp thất nghiệp phải thông báo tìm kiếm việc làm hằng tháng thế nào và thời gian tối đa được hưởng trợ cấp là bao lâu?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "LUAT_VIEC_LAM_2013",
                "article_number": "Điều 50",
                "chunk_ids": ["LUAT_VIEC_LAM_2013_Điều50_50"]
            },
            {
                "document_id": "LUAT_VIEC_LAM_2013",
                "article_number": "Điều 52",
                "chunk_ids": ["LUAT_VIEC_LAM_2013_Điều52_52"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 50 và Điều 52 Luật Việc làm 2013: Trong thời gian hưởng trợ cấp thất nghiệp, hằng tháng người lao động phải trực tiếp thông báo với trung tâm dịch vụ việc làm nơi đang hưởng trợ cấp về việc tìm kiếm việc làm (trừ trường hợp ốm đau, thai sản, tai nạn có xác nhận y tế hoặc bất khả kháng). Thời gian hưởng trợ cấp thất nghiệp được tính theo số tháng đóng BHTN (đóng đủ 12 đến 36 tháng hưởng 03 tháng, sau đó cứ thêm 12 tháng hưởng thêm 01 tháng), nhưng tổng thời gian hưởng tối đa không quá 12 tháng.",
        "requires_refusal": False
    },
    {
        "question_id": "Q107",
        "question": "So sánh mức lương tối thiểu tháng và tối thiểu giờ giữa Vùng I và Vùng IV theo Nghị định 74/2024/NĐ-CP và nguyên tắc áp dụng khi doanh nghiệp có chi nhánh ở nhiều vùng?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "ND_74_2024",
                "article_number": "Điều 3",
                "chunk_ids": ["ND_74_2024_Điều3_Khoản1_2"]
            },
            {
                "document_id": "ND_74_2024",
                "article_number": "Điều 4",
                "chunk_ids": ["ND_74_2024_Điều4_Khoản1_5"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 3 và Điều 4 Nghị định 74/2024/NĐ-CP: Mức lương tối thiểu tháng và giờ tại Vùng I là 4.960.000 đồng/tháng (23.800 đồng/giờ); tại Vùng IV là 3.450.000 đồng/tháng (16.600 đồng/giờ). Về nguyên tắc áp dụng: Người sử dụng lao động hoạt động trên địa bàn thuộc vùng nào thì áp dụng mức lương tối thiểu quy định đối với vùng đó. Trường hợp người sử dụng lao động có đơn vị, chi nhánh hoạt động trên các địa bàn có mức lương tối thiểu khác nhau thì đơn vị, chi nhánh hoạt động ở địa bàn nào phải áp dụng mức lương tối thiểu quy định đối với địa bàn đó.",
        "requires_refusal": False
    },
    {
        "question_id": "Q108",
        "question": "Thời gian làm việc để tính trợ cấp thôi việc được xác định thế nào và tiền lương làm căn cứ tính trợ cấp thôi việc theo Nghị định 145/2020/NĐ-CP là gì?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "ND_145_2020",
                "article_number": "Điều 8",
                "chunk_ids": ["ND_145_2020_Điều8_Khoản1_15"]
            },
            {
                "document_id": "ND_145_2020",
                "article_number": "Điều 9",
                "chunk_ids": ["ND_145_2020_Điều9_Khoản1_23"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 8 và Điều 9 Nghị định 145/2020/NĐ-CP: Thời gian làm việc để tính trợ cấp thôi việc là tổng thời gian người lao động đã làm việc thực tế cho người sử dụng lao động trừ đi thời gian người lao động đã tham gia bảo hiểm thất nghiệp và thời gian làm việc đã được chi trả trợ cấp thôi việc, mất việc làm. Tiền lương để tính trợ cấp thôi việc là tiền lương bình quân theo hợp đồng lao động của 06 tháng liền kề trước khi người lao động thôi việc, bao gồm mức lương, phụ cấp lương và các khoản bổ sung khác xác định theo thỏa thuận.",
        "requires_refusal": False
    },
    {
        "question_id": "Q109",
        "question": "Những khoảng thời gian nào được tính vào thời giờ làm việc có hưởng lương và quy định về nghỉ giải lao giữa ca làm việc theo Nghị định 145/2020/NĐ-CP?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "ND_145_2020",
                "article_number": "Điều 58",
                "chunk_ids": ["ND_145_2020_Điều58_Khoản1_127"]
            },
            {
                "document_id": "ND_145_2020",
                "article_number": "Điều 59",
                "chunk_ids": ["ND_145_2020_Điều59_130"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 58 và Điều 59 Nghị định 145/2020/NĐ-CP: Các khoảng thời gian được tính vào thời giờ làm việc có hưởng lương gồm: nghỉ giữa giờ, nghỉ giải lao theo tính chất công việc, nghỉ mỗi ngày 60 phút đối với lao động nữ nuôi con dưới 12 tháng tuổi, nghỉ mỗi ngày 30 phút trong thời gian hành kinh, thời gian khám sức khỏe thai sản, thời gian học tập huấn luyện an toàn lao động... Người lao động làm việc theo ca liên tục từ 06 giờ trở lên được nghỉ giữa giờ ít nhất 30 phút (ban ngày) hoặc ít nhất 45 phút (ban đêm) và thời gian nghỉ này được tính vào giờ làm việc.",
        "requires_refusal": False
    },
    {
        "question_id": "Q110",
        "question": "Trình tự tổ chức đối thoại định kỳ tại nơi làm việc và số lượng thành viên đại diện tham gia đối thoại của mỗi bên theo Nghị định 145/2020/NĐ-CP?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "ND_145_2020",
                "article_number": "Điều 68",
                "chunk_ids": ["ND_145_2020_Điều68_139"]
            },
            {
                "document_id": "ND_145_2020",
                "article_number": "Điều 69",
                "chunk_ids": ["ND_145_2020_Điều69_Khoản1_140"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 68 và Điều 69 Nghị định 145/2020/NĐ-CP: Đối thoại tại nơi làm việc được tổ chức định kỳ ít nhất 01 năm một lần hoặc khi có yêu cầu của một hoặc các bên. Số lượng thành viên tham gia đối thoại của bên người sử dụng lao động ít nhất là 03 người và của bên người lao động ít nhất là 03 người, căn cứ theo quy mô lao động của doanh nghiệp do hai bên thỏa thuận xác định. Diễn biến cuộc đối thoại phải được ghi biên bản và công khai rộng rãi cho toàn thể người lao động tại doanh nghiệp.",
        "requires_refusal": False
    },
    {
        "question_id": "Q111",
        "question": "Những trường hợp nào người lao động nước ngoài không thuộc diện cấp giấy phép lao động và trình tự đề nghị cấp giấy xác nhận theo Nghị định 219/2025/NĐ-CP?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "ND_219_2025",
                "article_number": "Điều 9",
                "chunk_ids": ["ND_219_2025_Điều9_Khoản1_21"]
            },
            {
                "document_id": "ND_219_2025",
                "article_number": "Điều 11",
                "chunk_ids": ["ND_219_2025_Điều11_26"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 9 và Điều 11 Nghị định 219/2025/NĐ-CP: Các trường hợp không thuộc diện cấp giấy phép lao động bao gồm: chủ sở hữu hoặc thành viên góp vốn công ty TNHH có giá trị vốn góp theo quy định; luật sư nước ngoài đã được cấp giấy phép hành nghề tại Việt Nam; người nước ngoài kết hôn với người Việt Nam và sinh sống tại Việt Nam; vào làm việc dưới 30 ngày và không quá 03 lần trong một năm... Người sử dụng lao động nộp hồ sơ đề nghị cơ quan chuyên môn về lao động cấp tỉnh cấp Giấy xác nhận không thuộc diện cấp giấy phép lao động trước ít nhất 10 ngày làm việc kể từ ngày người lao động dự kiến bắt đầu làm việc.",
        "requires_refusal": False
    },
    {
        "question_id": "Q112",
        "question": "Người lao động nước ngoài cần đáp ứng những điều kiện gì để được cấp giấy phép lao động và hồ sơ xin cấp gồm những tài liệu chính nào theo Nghị định 219/2025/NĐ-CP?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "ND_219_2025",
                "article_number": "Điều 12",
                "chunk_ids": ["ND_219_2025_Điều12_27"]
            },
            {
                "document_id": "ND_219_2025",
                "article_number": "Điều 13",
                "chunk_ids": ["ND_219_2025_Điều13_28"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 12 và Điều 13 Nghị định 219/2025/NĐ-CP: Điều kiện cấp giấy phép lao động: đủ 18 tuổi trở lên, có năng lực hành vi dân sự đầy đủ; có trình độ chuyên môn, tay nghề, kinh nghiệm làm việc phù hợp; có đủ sức khỏe theo quy định; không phải là người đang trong thời gian chấp hành hình phạt hoặc chưa được xóa án tích; và được cơ quan có thẩm quyền chấp thuận nhu cầu sử dụng lao động nước ngoài. Hồ sơ gồm: Văn bản đề nghị cấp giấy phép lao động; Giấy khám sức khỏe; Phiếu lý lịch tư pháp; Văn bản, giấy tờ chứng minh là nhà quản lý, giám đốc điều hành, chuyên gia hoặc lao động kỹ thuật; 02 ảnh màu và bản sao hộ chiếu.",
        "requires_refusal": False
    },
    {
        "question_id": "Q113",
        "question": "Hành vi không trả hoặc trả không đủ tiền lương làm thêm giờ bị xử phạt hành chính thế nào và nguyên tắc áp dụng mức phạt đối với tổ chức vi phạm theo Nghị định 12/2022/NĐ-CP?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "ND_12_2022",
                "article_number": "Điều 6",
                "chunk_ids": ["ND_12_2022_Điều6_C1_9"]
            },
            {
                "document_id": "ND_12_2022",
                "article_number": "Điều 12",
                "chunk_ids": ["ND_12_2022_Điều12_Khoản1_29"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 6 và Điều 12 Nghị định 12/2022/NĐ-CP: Hành vi không trả hoặc trả không đủ tiền lương làm thêm giờ, tiền lương làm việc vào ban đêm cho người lao động bị phạt tiền theo các mức lũy tiến tùy theo số lượng người lao động bị vi phạm: từ 5.000.000 đồng đến 10.000.000 đồng (từ 01 đến 10 người); đến mức cao nhất từ 40.000.000 đồng đến 50.000.000 đồng (từ 301 người trở lên). Mức phạt tiền này là mức phạt áp dụng đối với cá nhân; mức phạt tiền đối với tổ chức bằng 02 lần mức phạt tiền đối với cá nhân.",
        "requires_refusal": False
    },
    {
        "question_id": "Q114",
        "question": "Mức phạt tiền đối với hành vi huy động người lao động làm thêm giờ vượt quá số giờ quy định hoặc không cho người lao động nghỉ phép năm theo Nghị định 12/2022/NĐ-CP là bao nhiêu?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "ND_12_2022",
                "article_number": "Điều 14",
                "chunk_ids": ["ND_12_2022_Điều14_Khoản1_P1_43"]
            },
            {
                "document_id": "ND_12_2022",
                "article_number": "Điều 15",
                "chunk_ids": ["ND_12_2022_Điều15_46"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 14 và Điều 15 Nghị định 12/2022/NĐ-CP: Phạt tiền từ 20.000.000 đồng đến 25.000.000 đồng đối với người sử dụng lao động có hành vi huy động người lao động làm thêm giờ vượt quá số giờ quy định tại luật; hoặc phạt từ 50.000.000 đồng đến 75.000.000 đồng nếu huy động làm thêm giờ mà không được sự đồng ý của người lao động. Đối với hành vi không bảo đảm cho người lao động nghỉ việc riêng, nghỉ không hưởng lương hoặc không giải quyết chế độ nghỉ phép hằng năm theo luật định thì bị phạt tiền từ 10.000.000 đồng đến 20.000.000 đồng (mức phạt áp dụng với cá nhân, tổ chức phạt gấp 2 lần).",
        "requires_refusal": False
    },
    {
        "question_id": "Q115",
        "question": "Lộ trình tuổi nghỉ hưu của người lao động trong điều kiện bình thường và các trường hợp người lao động được nghỉ hưu ở tuổi thấp hơn theo Nghị định 135/2020/NĐ-CP?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "ND_135_2020",
                "article_number": "Điều 4",
                "chunk_ids": ["ND_135_2020_Điều4_Khoản1_3"]
            },
            {
                "document_id": "ND_135_2020",
                "article_number": "Điều 5",
                "chunk_ids": ["ND_135_2020_Điều5_Khoản1_5"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 4 và Điều 5 Nghị định 135/2020/NĐ-CP: Kể từ ngày 01/01/2021, tuổi nghỉ hưu của người lao động trong điều kiện bình thường là đủ 60 tuổi 03 tháng đối với nam và đủ 55 tuổi 04 tháng đối với nữ; sau đó mỗi năm tăng thêm 03 tháng đối với nam cho đến khi đủ 62 tuổi vào năm 2028, và tăng thêm 04 tháng đối với nữ cho đến khi đủ 60 tuổi vào năm 2035. Người lao động có thể nghỉ hưu ở tuổi thấp hơn nhưng không quá 05 tuổi so với tuổi quy định tại thời điểm nghỉ hưu nếu có từ đủ 15 năm làm nghề, công việc nặng nhọc, độc hại, nguy hiểm hoặc làm việc ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn, hoặc bị suy giảm khả năng lao động từ 61% trở lên.",
        "requires_refusal": False
    },
    {
        "question_id": "Q116",
        "question": "Thời hạn báo trước khi đơn phương chấm dứt hợp đồng lao động của người lao động và người sử dụng lao động theo Bộ luật Lao động 2019?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 35",
                "chunk_ids": ["BLLD_2019_Điều35_Khoản1_48"]
            },
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 36",
                "chunk_ids": ["BLLD_2019_Điều36_Khoản1_P1_50"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 35 và Điều 36 Bộ luật Lao động 2019: Cả người lao động và người sử dụng lao động khi đơn phương chấm dứt hợp đồng lao động phải báo trước: ít nhất 45 ngày đối với hợp đồng lao động không xác định thời hạn; ít nhất 30 ngày đối với hợp đồng lao động xác định thời hạn từ 12 tháng đến 36 tháng; ít nhất 03 ngày làm việc đối với hợp đồng lao động xác định thời hạn dưới 12 tháng. Người lao động có quyền đơn phương chấm dứt HĐLĐ không cần báo trước trong một số trường hợp luật định (bị ngược đãi, quấy rối tình dục, không được trả lương đúng hạn...).",
        "requires_refusal": False
    },
    {
        "question_id": "Q117",
        "question": "Quy định về số ngày nghỉ phép hằng năm cơ bản của người lao động và nguyên tắc tăng thêm ngày nghỉ phép theo thâm niên làm việc theo Bộ luật Lao động 2019?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 113",
                "chunk_ids": ["BLLD_2019_Điều113_Khoản1_149"]
            },
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 114",
                "chunk_ids": ["BLLD_2019_Điều114_152"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 113 và Điều 114 Bộ luật Lao động 2019: Người lao động làm việc đủ 12 tháng cho một người sử dụng lao động được nghỉ hằng năm hưởng nguyên lương: 12 ngày làm việc đối với công việc trong điều kiện bình thường; 14 ngày làm việc đối với lao động chưa thành niên, lao động là người khuyết tật, người làm nghề, công việc nặng nhọc, độc hại, nguy hiểm; 16 ngày làm việc đối với người làm nghề, công việc đặc biệt nặng nhọc, độc hại, nguy hiểm. Về thâm niên: Cứ đủ 05 năm làm việc cho một người sử dụng lao động thì số ngày nghỉ hằng năm của người lao động được tăng thêm tương ứng 01 ngày.",
        "requires_refusal": False
    },
    {
        "question_id": "Q118",
        "question": "Người sử dụng lao động có những trách nhiệm gì về bảo vệ thai sản và bảo đảm việc làm cho lao động nữ sau khi nghỉ thai sản theo Bộ luật Lao động 2019?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 137",
                "chunk_ids": ["BLLD_2019_Điều137_Khoản1_180"]
            },
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 140",
                "chunk_ids": ["BLLD_2019_Điều140_186"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 137 và Điều 140 Bộ luật Lao động 2019: Người sử dụng lao động không được sử dụng lao động nữ làm việc ban đêm, làm thêm giờ và đi công tác xa khi mang thai từ tháng thứ 7 (hoặc tháng thứ 6 nếu làm việc ở vùng cao, biên giới, hải đảo) hoặc đang nuôi con dưới 12 tháng tuổi; không được sa thải hoặc đơn phương chấm dứt HĐLĐ vì lý do kết hôn, mang thai, nghỉ thai sản, nuôi con dưới 12 tháng tuổi. Người lao động được bảo đảm việc làm cũ khi trở lại làm việc sau khi hết thời gian nghỉ thai sản mà không bị giảm tiền lương và quyền, lợi ích; nếu việc làm cũ không còn thì bố trí việc làm khác với mức lương không thấp hơn.",
        "requires_refusal": False
    },
    {
        "question_id": "Q119",
        "question": "Chế độ thời giờ làm việc đối với lao động không thường xuyên và quy định về làm thêm giờ trong lĩnh vực thăm dò dầu khí trên biển theo Thông tư 20/2023/TT-BCT?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "TT_20_2023",
                "article_number": "Điều 5",
                "chunk_ids": ["TT_20_2023_Điều5_Khoản1_4"]
            },
            {
                "document_id": "TT_20_2023",
                "article_number": "Điều 6",
                "chunk_ids": ["TT_20_2023_Điều6_7"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 5 và Điều 6 Thông tư 20/2023/TT-BCT: Người lao động làm việc không thường xuyên trên biển được áp dụng thời giờ làm việc theo phiên và ca làm việc: ca làm việc không quá 12 giờ/ngày và thời gian làm việc của một phiên không quá 28 ngày (trường hợp đặc biệt do sự cố kỹ thuật, thời tiết có thể kéo dài thêm nhưng không quá 14 ngày). Làm thêm giờ được thực hiện khi có sự đồng ý của người lao động, tổng số giờ làm việc bình thường và làm thêm giờ không quá 14 giờ trong 01 ngày; tổng số giờ làm thêm không quá 300 giờ trong 01 năm.",
        "requires_refusal": False
    },
    {
        "question_id": "Q120",
        "question": "Quy định về việc giao kết hợp đồng và hồ sơ đề nghị sử dụng người chưa đủ 13 tuổi làm việc trong các công việc nghệ thuật, thể thao theo Thông tư 09/2020/TT-BLĐTBXH?",
        "category": "single_doc_multi_chunk",
        "gold_sources": [
            {
                "document_id": "TT_09_2020",
                "article_number": "Điều 4",
                "chunk_ids": ["TT_09_2020_Điều4_Khoản1_6"]
            },
            {
                "document_id": "TT_09_2020",
                "article_number": "Điều 6",
                "chunk_ids": ["TT_09_2020_Điều6_Khoản1_9"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 4 và Điều 6 Thông tư 09/2020/TT-BLĐTBXH: Người sử dụng lao động phải giao kết hợp đồng lao động bằng văn bản với người chưa đủ 13 tuổi và người đại diện theo pháp luật của người đó; hợp đồng phải có chữ ký của cả người đại diện và người chưa đủ 13 tuổi. Trước khi tuyển dụng, người sử dụng lao động phải gửi hồ sơ đề nghị tới Sở Lao động - Thương binh và Xã hội gồm: Văn bản đề nghị; Phiếu khám sức khỏe; Bản cam kết bảo đảm điều kiện học tập, sinh hoạt, an toàn cho trẻ em; và có sự đồng ý bằng văn bản của Sở LĐTBXH trước khi bắt đầu sử dụng lao động.",
        "requires_refusal": False
    }
]

