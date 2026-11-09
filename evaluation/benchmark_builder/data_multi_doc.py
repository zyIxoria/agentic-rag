"""Multi Document Questions (Q121 - Q153)."""

QUESTIONS_MULTI_DOCUMENT = [
    {
        "question_id": "Q121",
        "question": "Mức lương tối thiểu theo quy định chung tại Bộ luật Lao động 2019 và số tiền lương tối thiểu tháng cụ thể đối với người lao động làm việc tại Vùng I theo Nghị định 74/2024/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 91",
                "chunk_ids": ["BLLD_2019_Điều91_125"]
            },
            {
                "document_id": "ND_74_2024",
                "article_number": "Điều 3",
                "chunk_ids": ["ND_74_2024_Điều3_Khoản1_2"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 91 Bộ luật Lao động 2019 và Điều 3 Nghị định 74/2024/NĐ-CP: Mức lương tối thiểu là mức lương thấp nhất được trả cho người lao động làm công việc giản đơn nhất trong điều kiện lao động bình thường nhằm bảo đảm mức sống tối thiểu của người lao động và gia đình họ, được xác lập theo vùng và do Chính phủ quyết định trên cơ sở khuyến nghị của Hội đồng tiền lương quốc gia. Theo quy định cụ thể tại Nghị định 74/2024/NĐ-CP, mức lương tối thiểu tháng áp dụng cho người lao động làm việc tại Vùng I là 4.960.000 đồng/tháng (mức lương tối thiểu giờ là 23.800 đồng/giờ).",
        "requires_refusal": False
    },
    {
        "question_id": "Q122",
        "question": "Trần thời giờ làm việc bình thường theo Bộ luật Lao động 2019 và các khoảng thời gian nghỉ ngơi được tính vào thời giờ làm việc có hưởng lương theo Nghị định 145/2020/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 105",
                "chunk_ids": ["BLLD_2019_Điều105_139"]
            },
            {
                "document_id": "ND_145_2020",
                "article_number": "Điều 58",
                "chunk_ids": ["ND_145_2020_Điều58_Khoản1_127"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 105 Bộ luật Lao động 2019 và Điều 58 Nghị định 145/2020/NĐ-CP: Thời giờ làm việc bình thường không quá 08 giờ trong 01 ngày và không quá 48 giờ trong 01 tuần (khuyến khích tuần 40 giờ). Các khoảng thời gian được tính vào giờ làm việc có hưởng lương gồm: nghỉ giữa giờ khi làm việc ca từ 6 giờ trở lên (nghỉ 30 phút ban ngày hoặc 45 phút ban đêm); nghỉ giải lao theo tính chất công việc; nghỉ 60 phút mỗi ngày đối với lao động nữ nuôi con dưới 12 tháng tuổi; nghỉ 30 phút mỗi ngày trong thời gian hành kinh; thời gian khám sức khỏe thai sản; thời gian học tập huấn luyện an toàn lao động...",
        "requires_refusal": False
    },
    {
        "question_id": "Q123",
        "question": "Quy định về trợ cấp thôi việc tại Điều 46 Bộ luật Lao động 2019 kết hợp với cách xác định thời gian làm việc để tính trợ cấp theo Nghị định 145/2020/NĐ-CP được thực hiện như thế nào?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 46",
                "chunk_ids": ["BLLD_2019_Điều46_66"]
            },
            {
                "document_id": "ND_145_2020",
                "article_number": "Điều 8",
                "chunk_ids": ["ND_145_2020_Điều8_Khoản1_15"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 46 Bộ luật Lao động 2019 và Điều 8 Nghị định 145/2020/NĐ-CP: Khi hợp đồng lao động chấm dứt hợp pháp, người sử dụng lao động có trách nhiệm trả trợ cấp thôi việc cho người lao động đã làm việc thường xuyên từ đủ 12 tháng trở lên, mỗi năm làm việc được trợ cấp một nửa tháng tiền lương. Thời gian làm việc để tính trợ cấp thôi việc là tổng thời gian người lao động đã làm việc thực tế cho người sử dụng lao động trừ đi thời gian người lao động đã tham gia bảo hiểm thất nghiệp theo quy định của pháp luật và thời gian làm việc đã được người sử dụng lao động chi trả trợ cấp thôi việc, trợ cấp mất việc làm.",
        "requires_refusal": False
    },
    {
        "question_id": "Q124",
        "question": "Quyền của người lao động được từ chối làm việc khi thấy rõ nguy cơ xảy ra tai nạn lao động đe dọa nghiêm trọng tính mạng được quy định thế nào giữa Bộ luật Lao động 2019 và Luật An toàn, vệ sinh lao động 2015?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 5",
                "chunk_ids": ["BLLD_2019_Điều5_Khoản1_9"]
            },
            {
                "document_id": "LUAT_ATVSLD_2015",
                "article_number": "Điều 6",
                "chunk_ids": ["LUAT_ATVSLD_2015_Điều6_Khoản1_P1_9"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 5 Bộ luật Lao động 2019 và Điều 6 Luật An toàn, vệ sinh lao động 2015: Người lao động có quyền từ chối làm việc hoặc rời bỏ nơi làm việc mà vẫn được trả đủ tiền lương và không bị coi là vi phạm kỷ luật lao động khi thấy rõ nguy cơ xảy ra tai nạn lao động đe dọa nghiêm trọng tính mạng hoặc sức khỏe của mình, nhưng phải báo ngay cho người quản lý trực tiếp biết. Người sử dụng lao động không được buộc người lao động tiếp tục làm việc hoặc trở lại nơi làm việc khi nguy cơ đó chưa được khắc phục.",
        "requires_refusal": False
    },
    {
        "question_id": "Q125",
        "question": "Thời gian nghỉ việc hưởng chế độ thai sản của lao động nữ theo Điều 139 Bộ luật Lao động 2019 kết hợp với mức hưởng trợ cấp thai sản theo Luật Bảo hiểm xã hội 2024?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 139",
                "chunk_ids": ["BLLD_2019_Điều139_Khoản1_184"]
            },
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 53",
                "chunk_ids": ["LUAT_BHXH_2024_Điều53_Khoản1_115"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 139 Bộ luật Lao động 2019 và Điều 53 Luật Bảo hiểm xã hội 2024: Lao động nữ được nghỉ thai sản trước và sau khi sinh con là 06 tháng; thời gian nghỉ trước khi sinh không quá 02 tháng. Trường hợp lao động nữ sinh đôi trở lên thì từ con thứ hai trở đi, cứ mỗi con, người mẹ được nghỉ thêm 01 tháng. Trong thời gian nghỉ thai sản, người lao động đủ điều kiện đóng BHXH được quỹ bảo hiểm xã hội chi trả trợ cấp thai sản theo quy định của Luật Bảo hiểm xã hội.",
        "requires_refusal": False
    },
    {
        "question_id": "Q126",
        "question": "So sánh điều kiện về số năm đóng bảo hiểm xã hội tối thiểu để hưởng lương hưu giữa Luật Bảo hiểm xã hội 2014 và Luật Bảo hiểm xã hội 2024?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "LUAT_BHXH_2014",
                "article_number": "Điều 54",
                "chunk_ids": ["LUAT_BHXH_2014_Điều54_Khoản1_74"]
            },
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 64",
                "chunk_ids": ["LUAT_BHXH_2024_Điều64_Khoản1_P1_143"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 54 Luật Bảo hiểm xã hội 2014 và Điều 64 Luật Bảo hiểm xã hội 2024: Theo Luật BHXH 2014, người lao động đủ tuổi nghỉ hưu phải có thời gian đóng bảo hiểm xã hội từ đủ 20 năm trở lên mới đủ điều kiện hưởng lương hưu hằng tháng. Trong khi đó, theo quy định cải cách tại Luật BHXH 2024 (có hiệu lực từ 01/07/2025), thời gian đóng bảo hiểm xã hội tối thiểu để hưởng lương hưu đã được giảm xuống còn từ đủ 15 năm trở lên, tạo cơ hội cho những người tham gia muộn hoặc có thời gian đóng ngắt quãng được hưởng lương hưu.",
        "requires_refusal": False
    },
    {
        "question_id": "Q127",
        "question": "So sánh nhóm đối tượng tham gia bảo hiểm xã hội bắt buộc giữa Luật Bảo hiểm xã hội 2014 và Luật Bảo hiểm xã hội 2024 đối với chủ hộ kinh doanh và người làm việc không trọn thời gian?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "LUAT_BHXH_2014",
                "article_number": "Điều 2",
                "chunk_ids": ["LUAT_BHXH_2014_Điều2_Khoản1_P1_1"]
            },
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 2",
                "chunk_ids": ["LUAT_BHXH_2024_Điều2_Khoản1_P1_1"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 2 Luật Bảo hiểm xã hội 2014 và Điều 2 Luật Bảo hiểm xã hội 2024: Luật BHXH 2014 chủ yếu áp dụng BHXH bắt buộc đối với người làm việc theo HĐLĐ từ đủ 01 tháng trở lên, cán bộ công chức viên chức, sĩ quan lực lượng vũ trang... Luật BHXH 2024 đã mở rộng diện bao phủ, bổ sung thêm các nhóm bắt buộc tham gia gồm: chủ hộ kinh doanh của hộ kinh doanh có đăng ký kinh doanh; người làm việc không trọn thời gian có mức tiền lương trong tháng bằng hoặc cao hơn mức tiền lương làm căn cứ đóng BHXH bắt buộc thấp nhất; và người quản lý doanh nghiệp, kiểm soát viên không hưởng tiền lương.",
        "requires_refusal": False
    },
    {
        "question_id": "Q128",
        "question": "Tuổi nghỉ hưu của người lao động trong điều kiện bình thường theo Điều 169 Bộ luật Lao động 2019 và bảng lộ trình tăng tuổi nghỉ hưu theo Nghị định 135/2020/NĐ-CP được xác định như thế nào?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 169",
                "chunk_ids": ["BLLD_2019_Điều169_Khoản1_218"]
            },
            {
                "document_id": "ND_135_2020",
                "article_number": "Điều 4",
                "chunk_ids": ["ND_135_2020_Điều4_Khoản1_3"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 169 Bộ luật Lao động 2019 và Điều 4 Nghị định 135/2020/NĐ-CP: Tuổi nghỉ hưu của người lao động trong điều kiện bình thường được điều chỉnh theo lộ trình cho đến khi đủ 62 tuổi đối với lao động nam vào năm 2028 và đủ 60 tuổi đối với lao động nữ vào năm 2035. Kể từ ngày 01/01/2021, tuổi nghỉ hưu là đủ 60 tuổi 03 tháng đối với nam và đủ 55 tuổi 04 tháng đối với nữ; sau đó mỗi năm tăng thêm 03 tháng đối với lao động nam và tăng thêm 04 tháng đối với lao động nữ.",
        "requires_refusal": False
    },
    {
        "question_id": "Q129",
        "question": "Điều kiện người lao động nước ngoài làm việc tại Việt Nam theo Điều 151 Bộ luật Lao động 2019 và quy định miễn giấy phép lao động khi kết hôn với người Việt Nam theo Nghị định 152/2020/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 151",
                "chunk_ids": ["BLLD_2019_Điều151_Khoản1_199"]
            },
            {
                "document_id": "ND_152_2020",
                "article_number": "Điều 9",
                "chunk_ids": ["ND_152_2020_Điều9_Khoản1_28"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 151 Bộ luật Lao động 2019 và khoản 8 Điều 9 Nghị định 152/2020/NĐ-CP: Người lao động nước ngoài làm việc tại Việt Nam phải đủ 18 tuổi trở lên, có năng lực hành vi dân sự đầy đủ, có trình độ chuyên môn, sức khỏe phù hợp, không vi phạm pháp luật hình sự và phải có giấy phép lao động do cơ quan nhà nước có thẩm quyền cấp, trừ trường hợp không thuộc diện cấp giấy phép lao động. Theo Nghị định 152/2020/NĐ-CP, người lao động nước ngoài kết hôn với người Việt Nam và sinh sống trên lãnh thổ Việt Nam thuộc trường hợp không thuộc diện cấp giấy phép lao động.",
        "requires_refusal": False
    },
    {
        "question_id": "Q130",
        "question": "Sự thay đổi về tiêu chuẩn xác định 'chuyên gia' nước ngoài giữa Nghị định 152/2020/NĐ-CP và Nghị định 70/2023/NĐ-CP được quy định như thế nào?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "ND_152_2020",
                "article_number": "Điều 3",
                "chunk_ids": ["ND_152_2020_Điều3_Khoản1_5"]
            },
            {
                "document_id": "ND_70_2023",
                "article_number": "Điều 1",
                "chunk_ids": ["ND_70_2023_Điều1_Khoản1_0"]
            }
        ],
        "reference_answer": "Căn cứ theo khoản 3 Điều 3 Nghị định 152/2020/NĐ-CP và khoản 1 Điều 1 Nghị định 70/2023/NĐ-CP: Trước đây Nghị định 152 yêu cầu chuyên gia phải tốt nghiệp đại học trở lên hoặc tương đương và có ít nhất 3 năm kinh nghiệm làm việc phù hợp với chuyên ngành được đào tạo. Nghị định 70/2023/NĐ-CP đã sửa đổi theo hướng tạo điều kiện thuận lợi hơn: chuyên gia chỉ cần có bằng đại học trở lên hoặc tương đương và có ít nhất 3 năm kinh nghiệm làm việc phù hợp với vị trí công việc mà người lao động nước ngoài dự kiến làm việc tại Việt Nam (không bắt buộc kinh nghiệm phải hoàn toàn trùng khớp với chuyên ngành đào tạo đại học).",
        "requires_refusal": False
    },
    {
        "question_id": "Q131",
        "question": "Chính sách đối với lao động nước ngoài kết hôn với người Việt Nam: việc miễn giấy phép lao động theo Nghị định 152/2020/NĐ-CP và quy định kế thừa trong Nghị định 219/2025/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "ND_152_2020",
                "article_number": "Điều 9",
                "chunk_ids": ["ND_152_2020_Điều9_Khoản1_28"]
            },
            {
                "document_id": "ND_219_2025",
                "article_number": "Điều 9",
                "chunk_ids": ["ND_219_2025_Điều9_Khoản1_21"]
            }
        ],
        "reference_answer": "Căn cứ theo khoản 8 Điều 9 Nghị định 152/2020/NĐ-CP và khoản 8 Điều 9 Nghị định 219/2025/NĐ-CP: Cả hai văn bản đều quy định nhất quán người lao động nước ngoài kết hôn với người Việt Nam và sinh sống trên lãnh thổ Việt Nam thuộc trường hợp không thuộc diện cấp giấy phép lao động, đồng thời được miễn thủ tục đề nghị cấp giấy xác nhận không thuộc diện cấp giấy phép lao động nhưng người sử dụng lao động phải báo cáo cơ quan chuyên môn về lao động.",
        "requires_refusal": False
    },
    {
        "question_id": "Q132",
        "question": "Đối tượng cán bộ, công chức lãnh đạo nữ được nghỉ hưu ở tuổi cao hơn theo Nghị định 83/2022/NĐ-CP và nội dung sửa đổi, bổ sung chức danh tại Nghị định 99/2024/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "ND_83_2022",
                "article_number": "Điều 2",
                "chunk_ids": ["ND_83_2022_Điều2_Khoản1_P1_1"]
            },
            {
                "document_id": "ND_99_2024",
                "article_number": "Điều 1",
                "chunk_ids": ["ND_99_2024_Điều1_0"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 2 Nghị định 83/2022/NĐ-CP và Điều 1 Nghị định 99/2024/NĐ-CP: Nghị định 83/2022 quy định các chức danh cán bộ, công chức nữ giữ chức vụ lãnh đạo, quản lý được nghỉ hưu ở tuổi cao hơn (như Phó Trưởng Ban Đảng, Phó Chủ tịch HĐND/UBND cấp tỉnh, Phó Cục trưởng, Vụ phó...). Nghị định 99/2024/NĐ-CP đã sửa đổi, bổ sung điểm p khoản 1 Điều 2 để hoàn thiện danh mục chức danh tương đương trong các cơ quan tư pháp và cơ quan ngành dọc, bảo đảm quyền lợi nghỉ hưu ở tuổi cao hơn tối đa 05 năm.",
        "requires_refusal": False
    },
    {
        "question_id": "Q133",
        "question": "Giới hạn thời gian thử việc theo Điều 25 Bộ luật Lao động 2019 và mức phạt tiền đối với hành vi yêu cầu thử việc quá thời gian quy định theo Nghị định 12/2022/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 25",
                "chunk_ids": ["BLLD_2019_Điều25_35"]
            },
            {
                "document_id": "ND_12_2022",
                "article_number": "Điều 9",
                "chunk_ids": ["ND_12_2022_Điều9_Khoản2_20"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 25 Bộ luật Lao động 2019 và khoản 2 Điều 9 Nghị định 12/2022/NĐ-CP: Thời gian thử việc do hai bên thỏa thuận nhưng chỉ được thử việc một lần cho một công việc và không quá: 180 ngày đối với người quản lý doanh nghiệp; 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ từ cao đẳng trở lên; 30 ngày đối với công việc cần trình độ trung cấp, công nhân kỹ thuật; 06 ngày làm việc đối với công việc khác. Nếu người sử dụng lao động yêu cầu thử việc vượt quá thời gian quy định thì bị phạt tiền từ 2.000.000 đồng đến 5.000.000 đồng (đối với cá nhân, tổ chức phạt gấp đôi) và phải trả đủ tiền lương cho người lao động.",
        "requires_refusal": False
    },
    {
        "question_id": "Q134",
        "question": "Hành vi người sử dụng lao động giữ bản chính giấy tờ tùy thân, văn bằng của người lao động bị nghiêm cấm tại Điều 17 Bộ luật Lao động 2019 và bị phạt bao nhiêu theo Nghị định 12/2022/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 17",
                "chunk_ids": ["BLLD_2019_Điều17_23"]
            },
            {
                "document_id": "ND_12_2022",
                "article_number": "Điều 9",
                "chunk_ids": ["ND_12_2022_Điều9_Khoản2_20"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 17 Bộ luật Lao động 2019 và điểm a khoản 2 Điều 9 Nghị định 12/2022/NĐ-CP: Người sử dụng lao động bị nghiêm cấm giữ bản chính giấy tờ tùy thân, văn bằng, chứng chỉ của người lao động khi giao kết, thực hiện hợp đồng lao động. Nếu vi phạm, người sử dụng lao động bị phạt tiền từ 20.000.000 đồng đến 25.000.000 đồng đối với cá nhân vi phạm (từ 40.000.000 đồng đến 50.000.000 đồng đối với tổ chức) và bị buộc trả lại bản chính giấy tờ tùy thân, văn bằng, chứng chỉ đã giữ của người lao động.",
        "requires_refusal": False
    },
    {
        "question_id": "Q135",
        "question": "Nguyên tắc sử dụng lao động chưa thành niên theo Bộ luật Lao động 2019 và điều kiện người từ đủ 13 tuổi đến chưa đủ 15 tuổi chỉ được làm công việc nhẹ theo Thông tư 09/2020/TT-BLĐTBXH?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 144",
                "chunk_ids": ["BLLD_2019_Điều144_190"]
            },
            {
                "document_id": "TT_09_2020",
                "article_number": "Điều 3",
                "chunk_ids": ["TT_09_2020_Điều3_Khoản1_2"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 144 Bộ luật Lao động 2019 và Điều 3 Thông tư 09/2020/TT-BLĐTBXH: Lao động chưa thành niên chỉ được làm công việc phù hợp với sức khỏe để bảo đảm sự phát triển thể lực, trí lực, nhân cách; người sử dụng lao động phải quan tâm chăm sóc về lao động, tiền lương, sức khỏe, học tập. Người từ đủ 13 tuổi đến chưa đủ 15 tuổi chỉ được làm các công việc nhẹ theo danh mục do Bộ LĐTBXH ban hành, phải có sự đồng ý bằng văn bản của người đại diện theo pháp luật và bảo đảm thời giờ làm việc không ảnh hưởng đến thời gian học tập.",
        "requires_refusal": False
    },
    {
        "question_id": "Q136",
        "question": "Quy định về số ngày nghỉ phép hằng năm tăng thêm cho người làm công việc nặng nhọc, độc hại tại Điều 113 Bộ luật Lao động 2019 và việc xác định ngành nghề theo Thông tư 11/2020/TT-BLĐTBXH?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 113",
                "chunk_ids": ["BLLD_2019_Điều113_Khoản1_149"]
            },
            {
                "document_id": "TT_11_2020",
                "article_number": "Điều 1",
                "chunk_ids": ["TT_11_2020_Điều1_0"]
            }
        ],
        "reference_answer": "Căn cứ theo khoản 1 Điều 113 Bộ luật Lao động 2019 và Điều 1 Thông tư 11/2020/TT-BLĐTBXH: Người lao động làm nghề, công việc nặng nhọc, độc hại, nguy hiểm được nghỉ hằng năm 14 ngày làm việc; người làm nghề, công việc đặc biệt nặng nhọc, độc hại, nguy hiểm được nghỉ 16 ngày làm việc (nhiều hơn từ 2 đến 4 ngày so với công việc bình thường là 12 ngày). Danh mục cụ thể các nghề, công việc nặng nhọc, độc hại, nguy hiểm và đặc biệt nặng nhọc, độc hại, nguy hiểm được tra cứu và xác định theo Thông tư số 11/2020/TT-BLĐTBXH.",
        "requires_refusal": False
    },
    {
        "question_id": "Q137",
        "question": "So sánh giới hạn giờ làm thêm trong ngày giữa người lao động thông thường theo Điều 107 Bộ luật Lao động 2019 và người lao động làm việc trên biển theo Thông tư 20/2023/TT-BCT?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 107",
                "chunk_ids": ["BLLD_2019_Điều107_Khoản1_141"]
            },
            {
                "document_id": "TT_20_2023",
                "article_number": "Điều 6",
                "chunk_ids": ["TT_20_2023_Điều6_7"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 107 Bộ luật Lao động 2019 và Điều 6 Thông tư 20/2023/TT-BCT: Theo quy định chung của BLLĐ 2019, số giờ làm thêm của người lao động không quá 50% số giờ làm việc bình thường trong 01 ngày (tức không quá 4 giờ/ngày nếu làm việc 8 giờ/ngày). Đối với người lao động làm việc trong lĩnh vực thăm dò, khai thác dầu khí trên biển theo Thông tư 20/2023/TT-BCT, ca làm việc bình thường là 12 giờ/ngày, và tổng số giờ làm việc bình thường cộng với số giờ làm thêm không được quá 14 giờ trong 01 ngày (tức thời gian làm thêm tối đa không quá 02 giờ/ngày).",
        "requires_refusal": False
    },
    {
        "question_id": "Q138",
        "question": "Phân biệt trách nhiệm chi trả và điều kiện giữa Trợ cấp mất việc làm theo Điều 47 Bộ luật Lao động 2019 và Trợ cấp thất nghiệp theo Luật Việc làm 2013?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 47",
                "chunk_ids": ["BLLD_2019_Điều47_67"]
            },
            {
                "document_id": "LUAT_VIEC_LAM_2013",
                "article_number": "Điều 49",
                "chunk_ids": ["LUAT_VIEC_LAM_2013_Điều49_Khoản1_47"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 47 Bộ luật Lao động 2019 và Điều 49 Luật Việc làm 2013: Trợ cấp mất việc làm do người sử dụng lao động trực tiếp chi trả cho người lao động đã làm việc thường xuyên từ đủ 12 tháng trở lên bị mất việc làm do thay đổi cơ cấu, công nghệ hoặc sáp nhập, chia tách doanh nghiệp (mỗi năm làm việc trả 01 tháng lương, tối thiểu 02 tháng lương). Trong khi đó, Trợ cấp thất nghiệp do Quỹ bảo hiểm thất nghiệp (cơ quan BHXH) chi trả cho người lao động tham gia BHTN đủ điều kiện (đóng đủ 12 tháng trở lên trong 24 tháng trước khi nghỉ việc), không phân biệt lý do chấm dứt HĐLĐ (trừ trường hợp đơn phương trái luật hoặc hưởng lương hưu).",
        "requires_refusal": False
    },
    {
        "question_id": "Q139",
        "question": "Mối liên hệ giữa chế độ bồi thường tai nạn lao động của người sử dụng lao động theo Luật An toàn, vệ sinh lao động 2015 và chế độ trợ cấp tai nạn lao động từ Quỹ bảo hiểm theo Luật Bảo hiểm xã hội 2024?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "LUAT_ATVSLD_2015",
                "article_number": "Điều 38",
                "chunk_ids": ["LUAT_ATVSLD_2015_Điều38_Khoản1_101"]
            },
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 4",
                "chunk_ids": ["LUAT_BHXH_2024_Điều4_18"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 38 Luật An toàn, vệ sinh lao động 2015 và Điều 4 Luật Bảo hiểm xã hội 2024: Khi người lao động bị tai nạn lao động, họ được hưởng quyền lợi từ hai nguồn độc lập: 1. Nguồn từ người sử dụng lao động: NSDLĐ có trách nhiệm trả đủ tiền lương, chi phí y tế điều trị và bồi thường tai nạn lao động căn cứ theo tỷ lệ suy giảm khả năng lao động; 2. Nguồn từ Quỹ bảo hiểm xã hội (chế độ bảo hiểm tai nạn lao động, bệnh nghề nghiệp thuộc hệ thống BHXH bắt buộc): chi trả trợ cấp một lần hoặc hằng tháng cho người lao động suy giảm KNLĐ từ 5% trở lên.",
        "requires_refusal": False
    },
    {
        "question_id": "Q140",
        "question": "Quy định về tạm hoãn thực hiện hợp đồng lao động theo Điều 30 Bộ luật Lao động 2019 và nghĩa vụ tham gia đóng bảo hiểm xã hội bắt buộc trong thời gian tạm hoãn theo Luật Bảo hiểm xã hội 2024?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 30",
                "chunk_ids": ["BLLD_2019_Điều30_41"]
            },
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 33",
                "chunk_ids": ["LUAT_BHXH_2024_Điều33_Khoản1_77"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 30 Bộ luật Lao động 2019 và Điều 33 Luật Bảo hiểm xã hội 2024: Trong thời gian tạm hoãn thực hiện hợp đồng lao động (như đi nghĩa vụ quân sự, bị tạm giam, nghỉ việc riêng theo thỏa thuận...), người lao động không được hưởng lương và các quyền, lợi ích giao kết trong HĐLĐ trừ khi có thỏa thuận khác. Do không có tiền lương làm căn cứ đóng trong thời gian này, cả người lao động và người sử dụng lao động không phải đóng bảo hiểm xã hội bắt buộc, trừ trường hợp hai bên có thỏa thuận về việc người sử dụng lao động vẫn chi trả tiền lương và trích nộp BHXH theo luật định.",
        "requires_refusal": False
    },
    {
        "question_id": "Q141",
        "question": "Chức năng tư vấn mức lương tối thiểu của Hội đồng tiền lương quốc gia theo Điều 92 Bộ luật Lao động 2019 và cơ cấu các bên đại diện theo Quyết định 992/QĐ-TTg?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 92",
                "chunk_ids": ["BLLD_2019_Điều92_126"]
            },
            {
                "document_id": "QD_992_2025",
                "article_number": "Điều 1",
                "chunk_ids": ["QD_992_2025_Điều1_0"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 92 Bộ luật Lao động 2019 và Điều 1 Quyết định 992/QĐ-TTg: Hội đồng tiền lương quốc gia là cơ quan tư vấn cho Chính phủ về mức lương tối thiểu và chính sách tiền lương đối với người lao động. Hội đồng hoạt động theo cơ chế ba bên gồm đại diện của Bộ Lao động - Thương binh và Xã hội (Chủ tịch Hội đồng), đại diện của Tổng Liên đoàn Lao động Việt Nam (đại diện người lao động) và đại diện của tổ chức đại diện người sử dụng lao động ở trung ương (VCCI, Liên minh HTX Việt Nam) cùng các chuyên gia độc lập.",
        "requires_refusal": False
    },
    {
        "question_id": "Q142",
        "question": "Thỏa thuận bảo vệ bí mật kinh doanh, bí mật công nghệ theo Điều 21 Bộ luật Lao động 2019 và quy định về quyền yêu cầu bồi thường thiệt hại theo Thông tư 10/2020/TT-BLĐTBXH?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 21",
                "chunk_ids": ["BLLD_2019_Điều21_Khoản1_30"]
            },
            {
                "document_id": "TT_10_2020",
                "article_number": "Điều 4",
                "chunk_ids": ["TT_10_2020_Điều4_Khoản1_11"]
            }
        ],
        "reference_answer": "Căn cứ theo khoản 2 Điều 21 Bộ luật Lao động 2019 và Điều 4 Thông tư 10/2020/TT-BLĐTBXH: Khi người lao động làm việc có liên quan trực tiếp đến bí mật kinh doanh, công nghệ thì người sử dụng lao động có quyền thỏa thuận bằng văn bản về nội dung, thời hạn bảo vệ, quyền lợi và việc bồi thường khi vi phạm. Thỏa thuận có thể bao gồm: danh mục bí mật; phạm vi sử dụng; thời hạn bảo vệ; nghĩa vụ bồi thường thiệt hại và phương thức xử lý tranh chấp theo trọng tài hoặc tòa án khi người lao động vi phạm cam kết.",
        "requires_refusal": False
    },
    {
        "question_id": "Q143",
        "question": "Trình tự, thủ tục xử lý kỷ luật lao động theo Điều 122 Bộ luật Lao động 2019 và quy định về thông báo, thành phần cuộc họp xử lý kỷ luật theo Nghị định 145/2020/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 122",
                "chunk_ids": ["BLLD_2019_Điều122_Khoản1_162"]
            },
            {
                "document_id": "ND_145_2020",
                "article_number": "Điều 70",
                "chunk_ids": ["ND_145_2020_Điều70_Khoản1_145"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 122 Bộ luật Lao động 2019 và Điều 70 Nghị định 145/2020/NĐ-CP: Người sử dụng lao động phải chứng minh được lỗi của người lao động; phải có sự tham gia của tổ chức đại diện người lao động tại cơ sở; người lao động phải có mặt và có quyền tự bào chữa hoặc nhờ luật sư bào chữa; việc xử lý kỷ luật phải được lập biên bản. Trước khi họp xử lý kỷ luật ít nhất 05 ngày làm việc, người sử dụng lao động phải thông báo nội dung, thời gian, địa điểm họp cho các thành phần bắt buộc tham dự; trường hợp một trong các thành phần không xác nhận tham dự hoặc vắng mặt thì NSDLĐ vẫn tiến hành họp theo luật định.",
        "requires_refusal": False
    },
    {
        "question_id": "Q144",
        "question": "Định nghĩa hành vi quấy rối tình dục tại nơi làm việc theo Điều 84 Bộ luật Lao động 2019 và nội dung phòng, chống quấy rối tình dục bắt buộc trong nội quy lao động theo Nghị định 145/2020/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 84",
                "chunk_ids": ["BLLD_2019_Điều84_118"]
            },
            {
                "document_id": "ND_145_2020",
                "article_number": "Điều 85",
                "chunk_ids": ["ND_145_2020_Điều85_Khoản1_176"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 84 Bộ luật Lao động 2019 và Điều 85 Nghị định 145/2020/NĐ-CP: Quấy rối tình dục tại nơi làm việc là hành vi có tính chất tình dục của bất kỳ người nào đối với người khác tại nơi làm việc mà không được người đó mong muốn hoặc chấp thuận (thể hiện bằng hành vi thể chất, lời nói hoặc phi lời nói). Người sử dụng lao động có nghĩa vụ quy định trong nội quy lao động các biện pháp phòng chống quấy rối tình dục: quy định chi tiết các hành vi bị nghiêm cấm; trình tự, thủ tục khiếu nại, tố cáo và xử lý kỷ luật nghiêm khắc đối với người có hành vi quấy rối tình dục.",
        "requires_refusal": False
    },
    {
        "question_id": "Q145",
        "question": "Điều kiện nghỉ hưu khi suy giảm khả năng lao động theo Điều 55 Luật Bảo hiểm xã hội 2014 đối chiếu với lộ trình tăng tuổi nghỉ hưu của Nghị định 135/2020/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "LUAT_BHXH_2014",
                "article_number": "Điều 55",
                "chunk_ids": ["LUAT_BHXH_2014_Điều55_Khoản1_77"]
            },
            {
                "document_id": "ND_135_2020",
                "article_number": "Điều 5",
                "chunk_ids": ["ND_135_2020_Điều5_Khoản1_5"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 55 Luật Bảo hiểm xã hội 2014 và Điều 5 Nghị định 135/2020/NĐ-CP: Người lao động khi nghỉ việc có đủ 20 năm đóng BHXH trở lên bị suy giảm khả năng lao động từ 61% đến dưới 81% được hưởng lương hưu với mức tuổi thấp hơn tối đa 05 tuổi so với tuổi nghỉ hưu trong điều kiện bình thường (tuổi bình thường tăng theo lộ trình Nghị định 135/2020/NĐ-CP); nếu bị suy giảm khả năng lao động từ 81% trở lên thì tuổi nghỉ hưu thấp hơn tối đa 10 tuổi so với tuổi nghỉ hưu bình thường.",
        "requires_refusal": False
    },
    {
        "question_id": "Q146",
        "question": "Hành vi trả lương cho người lao động thấp hơn mức lương tối thiểu vùng quy định tại Nghị định 74/2024/NĐ-CP bị xử phạt mức tiền bao nhiêu theo Nghị định 12/2022/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "ND_74_2024",
                "article_number": "Điều 3",
                "chunk_ids": ["ND_74_2024_Điều3_Khoản1_2"]
            },
            {
                "document_id": "ND_12_2022",
                "article_number": "Điều 17",
                "chunk_ids": ["ND_12_2022_Điều17_Khoản3_52"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 3 Nghị định 74/2024/NĐ-CP và khoản 3 Điều 17 Nghị định 12/2022/NĐ-CP: Mức lương tối thiểu vùng do Chính phủ quy định tại Nghị định 74/2024/NĐ-CP là mức sàn thấp nhất người sử dụng lao động được phép trả. Hành vi trả lương cho người lao động thấp hơn mức lương tối thiểu vùng bị phạt tiền từ 20.000.000 đồng đến 75.000.000 đồng đối với người sử dụng lao động là cá nhân tùy theo số lượng người lao động bị vi phạm (tổ chức bị phạt gấp đôi, từ 40.000.000 đồng đến 150.000.000 đồng) và bị buộc trả đủ tiền lương cộng thêm khoản tiền lãi chậm trả.",
        "requires_refusal": False
    },
    {
        "question_id": "Q147",
        "question": "Nghĩa vụ đóng bảo hiểm thất nghiệp theo Luật Việc làm 2013 và chế tài xử phạt người sử dụng lao động chậm đóng hoặc không đóng BHTN cho người lao động theo Nghị định 12/2022/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "LUAT_VIEC_LAM_2013",
                "article_number": "Điều 43",
                "chunk_ids": ["LUAT_VIEC_LAM_2013_Điều43_Khoản1_40"]
            },
            {
                "document_id": "ND_12_2022",
                "article_number": "Điều 32",
                "chunk_ids": ["ND_12_2022_Điều32_Khoản1_124"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 43 Luật Việc làm 2013 và Điều 32 Nghị định 12/2022/NĐ-CP: Người sử dụng lao động có nghĩa vụ tham gia và đóng bảo hiểm thất nghiệp cho người lao động thuộc diện tham gia BHTN bắt buộc. Nếu người sử dụng lao động có hành vi chậm đóng, không đóng hoặc trốn đóng bảo hiểm thất nghiệp thì bị xử phạt tiền từ 12% đến 15% tổng số tiền phải đóng BHTN tại thời điểm lập biên bản (tối đa không quá 75.000.000 đồng đối với cá nhân, 150.000.000 đồng đối với tổ chức) và bị buộc truy nộp đủ số tiền nợ kèm tiền lãi chậm đóng.",
        "requires_refusal": False
    },
    {
        "question_id": "Q148",
        "question": "Nghĩa vụ khám sức khỏe định kỳ cho người lao động theo Luật An toàn, vệ sinh lao động 2015 và mức xử phạt hành vi không tổ chức khám sức khỏe theo Nghị định 12/2022/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "LUAT_ATVSLD_2015",
                "article_number": "Điều 21",
                "chunk_ids": ["LUAT_ATVSLD_2015_Điều21_Khoản1_57"]
            },
            {
                "document_id": "ND_12_2022",
                "article_number": "Điều 22",
                "chunk_ids": ["ND_12_2022_Điều22_Khoản1_69"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 21 Luật An toàn, vệ sinh lao động 2015 và khoản 2 Điều 22 Nghị định 12/2022/NĐ-CP: Người sử dụng lao động phải tổ chức khám sức khỏe định kỳ ít nhất 01 lần/năm cho người lao động (hoặc 06 tháng/lần đối với công việc nặng nhọc, độc hại). Hành vi không tổ chức khám sức khỏe định kỳ hoặc khám phát hiện bệnh nghề nghiệp cho người lao động bị phạt tiền từ 1.000.000 đồng đến 3.000.000 đồng trên mỗi người lao động bị vi phạm nhưng tối đa không quá 75.000.000 đồng đối với cá nhân (tối đa 150.000.000 đồng đối với tổ chức).",
        "requires_refusal": False
    },
    {
        "question_id": "Q149",
        "question": "Quy định bắt buộc có giấy phép lao động cho người lao động nước ngoài theo Nghị định 152/2020/NĐ-CP và mức xử phạt trục xuất đối với người nước ngoài làm việc không có giấy phép theo Nghị định 12/2022/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "ND_152_2020",
                "article_number": "Điều 9",
                "chunk_ids": ["ND_152_2020_Điều9_Khoản1_28"]
            },
            {
                "document_id": "ND_12_2022",
                "article_number": "Điều 32",
                "chunk_ids": ["ND_12_2022_Điều32_Khoản1_124"]
            }
        ],
        "reference_answer": "Căn cứ theo Nghị định 152/2020/NĐ-CP và Điều 32 Nghị định 12/2022/NĐ-CP: Người lao động nước ngoài làm việc tại Việt Nam phải có giấy phép lao động (trừ các trường hợp được miễn). Người lao động nước ngoài làm việc tại Việt Nam mà không có giấy phép lao động hoặc không có văn bản xác nhận không thuộc diện cấp giấy phép lao động sẽ bị áp dụng hình thức xử phạt vi phạm hành chính là trục xuất khỏi lãnh thổ Việt Nam; người sử dụng lao động sử dụng lao động nước ngoài không có giấy phép bị phạt tiền từ 30.000.000 đồng đến 75.000.000 đồng (tổ chức phạt gấp đôi).",
        "requires_refusal": False
    },
    {
        "question_id": "Q150",
        "question": "Trách nhiệm của người sử dụng lao động phải chi trả thêm khoản tiền tương đương mức đóng BHXH cho người lao động không thuộc diện tham gia BHXH bắt buộc theo Bộ luật Lao động 2019 và Luật Bảo hiểm xã hội 2024?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 168",
                "chunk_ids": ["BLLD_2019_Điều168_217"]
            },
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 2",
                "chunk_ids": ["LUAT_BHXH_2024_Điều2_Khoản1_P1_1"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 168 Bộ luật Lao động 2019 và Điều 2 Luật Bảo hiểm xã hội 2024: Đối với người lao động không thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc, bảo hiểm y tế, bảo hiểm thất nghiệp (ví dụ như người lao động đã đủ tuổi nghỉ hưu đang hưởng lương hưu hằng tháng giao kết HĐLĐ mới), người sử dụng lao động có trách nhiệm chi trả thêm cùng lúc với kỳ trả lương một khoản tiền cho người lao động tương đương với mức người sử dụng lao động đóng BHXH, BHYT, BHTN cho người lao động theo quy định.",
        "requires_refusal": False
    },
    {
        "question_id": "Q151",
        "question": "Nghĩa vụ trang bị phương tiện bảo vệ cá nhân theo Luật An toàn, vệ sinh lao động 2015 đối với người lao động làm việc thuộc Danh mục nghề nặng nhọc, độc hại ban hành theo Thông tư 11/2020/TT-BLĐTBXH?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "LUAT_ATVSLD_2015",
                "article_number": "Điều 23",
                "chunk_ids": ["LUAT_ATVSLD_2015_Điều23_62"]
            },
            {
                "document_id": "TT_11_2020",
                "article_number": "Điều 1",
                "chunk_ids": ["TT_11_2020_Điều1_0"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 23 Luật An toàn, vệ sinh lao động 2015 và Điều 1 Thông tư 11/2020/TT-BLĐTBXH: Người lao động làm việc tiếp xúc với yếu tố nguy hiểm, yếu tố có hại thuộc Danh mục nghề, công việc nặng nhọc, độc hại, nguy hiểm theo Thông tư 11/2020/TT-BLĐTBXH phải được người sử dụng lao động trang cấp đầy đủ phương tiện bảo vệ cá nhân đạt tiêu chuẩn chất lượng trong quá trình làm việc; người sử dụng lao động không được trả bằng tiền thay cho việc trang cấp phương tiện bảo vệ cá nhân.",
        "requires_refusal": False
    },
    {
        "question_id": "Q152",
        "question": "Quy định về hợp đồng lao động và trả tiền bảo hiểm xã hội đối với lao động là người giúp việc gia đình giữa Bộ luật Lao động 2019 và Nghị định 145/2020/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 161",
                "chunk_ids": ["BLLD_2019_Điều161_210"]
            },
            {
                "document_id": "ND_145_2020",
                "article_number": "Điều 89",
                "chunk_ids": ["ND_145_2020_Điều89_Khoản1_P1_186"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 161 Bộ luật Lao động 2019 và Điều 89 Nghị định 145/2020/NĐ-CP: Người sử dụng lao động phải giao kết hợp đồng lao động bằng văn bản với lao động là người giúp việc gia đình. Do người giúp việc gia đình không thuộc đối tượng tham gia BHXH bắt buộc, người sử dụng lao động có trách nhiệm trả cho người giúp việc gia đình cùng lúc với kỳ trả lương một khoản tiền tương đương với mức đóng bảo hiểm xã hội bắt buộc, bảo hiểm y tế thuộc trách nhiệm của người sử dụng lao động để người lao động tự tham gia bảo hiểm.",
        "requires_refusal": False
    },
    {
        "question_id": "Q153",
        "question": "Mối quan hệ giữa quy định tuổi nghỉ hưu trong Luật Bảo hiểm xã hội 2024 (dẫn chiếu Điều 169 Bộ luật Lao động 2019) và tuổi nghỉ hưu cụ thể của từng năm theo Nghị định 135/2020/NĐ-CP?",
        "category": "multi_document",
        "gold_sources": [
            {
                "document_id": "LUAT_BHXH_2024",
                "article_number": "Điều 64",
                "chunk_ids": ["LUAT_BHXH_2024_Điều64_Khoản1_P1_143"]
            },
            {
                "document_id": "ND_135_2020",
                "article_number": "Điều 4",
                "chunk_ids": ["ND_135_2020_Điều4_Khoản1_3"]
            }
        ],
        "reference_answer": "Căn cứ theo Điều 64 Luật Bảo hiểm xã hội 2024 và Điều 4 Nghị định 135/2020/NĐ-CP: Điều 64 Luật BHXH 2024 quy định điều kiện hưởng lương hưu gắn liền với việc người lao động đủ tuổi nghỉ hưu theo quy định tại khoản 2 Điều 169 Bộ luật Lao động 2019. Nghị định 135/2020/NĐ-CP là văn bản quy định chi tiết lộ trình tăng tuổi này cho từng năm (mỗi năm tăng 3 tháng với nam, 4 tháng với nữ). Do đó, tuổi hưởng lương hưu theo Luật BHXH 2024 được tính chính xác dựa theo bảng lộ trình tuổi nghỉ hưu tương ứng với năm sinh của người lao động tại Nghị định 135/2020/NĐ-CP.",
        "requires_refusal": False
    }
]
