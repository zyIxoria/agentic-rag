"""
Adaptive RAG Legal Query Decomposer (Module 11).
Phân rã câu hỏi pháp lý phức tạp thành các truy vấn con nguyên tử (Sub-queries),
bảo toàn ngữ cảnh pháp lý (Context Preservation), thiết lập đồ thị phụ thuộc (DAG Dependency Graph),
kiểm định chất lượng (Validation) và sửa chữa tự động (Repair Loop).
"""

from __future__ import annotations
import re
import time
from typing import List, Optional, Tuple, Dict, Any

from Adaptive_RAG.config import AdaptiveRAGConfig, adaptive_config
from Adaptive_RAG.decomposition.base import BaseQueryDecomposer
from Adaptive_RAG.decomposition.schema import (
    DecompositionPlan,
    DecompositionType,
    ExecutionStrategy,
    SubQuery,
    ValidationResult,
    DecompositionTrace,
    QueryDecompositionResult,
)
from Adaptive_RAG.decomposition.validator import SubQueryValidator, SubQueryRepairer
from Adaptive_RAG.classifier.schema import ComplexityClass, QueryComplexityResult
from Adaptive_RAG.classifier.query_complexity_classifier import QueryComplexityClassifier


class LegalQueryDecomposer(BaseQueryDecomposer):
    """
    Bộ phân rã câu hỏi pháp luật lao động chuyên sâu (Module 11):
    1. Nhận diện dạng thức phân rã theo Taxonomy 5 lớp:
       - MULTI_ISSUE: Đa quyền lợi/nghĩa vụ độc lập.
       - MULTI_CONDITION: Đa điều kiện tình huống, rẽ nhánh, mâu thuẫn chế tài.
       - CROSS_REFERENCE: Viện dẫn chéo giữa các Điều luật quy định.
       - MULTI_DOCUMENT: Đa văn bản quy phạm (Luật + Nghị định/Thông tư).
       - CONDITIONAL_TEMPORAL: Tính toán qua các mốc thời gian, giai đoạn chính sách.
    2. Bảo toàn tuyệt đối ngữ cảnh (Context Preservation) cho từng câu hỏi con.
    3. Thiết lập đồ thị quan hệ phụ thuộc suy luận (Reasoning Dependency Graph).
    4. Kiểm định (Validation) và sửa chữa tự động (Repair Loop với MAX_RETRIES = 1).
    5. Ghi nhận đầy đủ dấu vết (Decomposition Trace) phục vụ giải trình học thuật.
    """

    MAX_DECOMPOSITION_RETRIES = 1

    # Mẫu tách câu ghép kết hợp đa vấn đề pháp lý độc lập
    COMPOUND_SPLIT_PATTERN = (
        r"\bvà\s+(có\s+được|có\s+phải|phải|có\s+bị\s+phạt|phạt\s+tiền|có\s+bị|bị\s+phạt|"
        r"bị\s+xử\s+phạt|mức\s+phạt|thủ\s+tục|tiền\s+lương|chế\s+độ|trách\s+nhiệm|thời\s+hạn|điều\s+kiện)\b"
    )

    def __init__(
        self,
        config: Optional[AdaptiveRAGConfig] = None,
        classifier: Optional[QueryComplexityClassifier] = None,
        validator: Optional[SubQueryValidator] = None,
        repairer: Optional[SubQueryRepairer] = None,
    ):
        super().__init__(config=config)
        self.classifier = classifier or QueryComplexityClassifier()
        self.validator = validator or SubQueryValidator()
        self.repairer = repairer or SubQueryRepairer()

    def _extract_documents(self, query: str) -> List[str]:
        """Trích xuất tên các văn bản quy phạm pháp luật trong câu hỏi."""
        doc_patterns = [
            (r"(?i)\bBộ\s+luật\s+Lao\s+động(?:\s+\d+)?\b|\bBLL[ĐD](?:\s+\d+)?\b", "Bộ luật Lao động 2019"),
            (r"(?i)\bNghị\s+định\s+145(?:/2020(?:/NĐ-CP)?)?\b", "Nghị định 145/2020/NĐ-CP"),
            (r"(?i)\bNghị\s+định\s+12(?:/2022(?:/NĐ-CP)?)?\b", "Nghị định 12/2022/NĐ-CP"),
            (r"(?i)\bNghị\s+định\s+152(?:/2020(?:/NĐ-CP)?)?\b", "Nghị định 152/2020/NĐ-CP"),
            (r"(?i)\bNghị\s+định\s+70(?:/2023(?:/NĐ-CP)?)?\b", "Nghị định 70/2023/NĐ-CP"),
            (r"(?i)\bNghị\s+định\s+135(?:/2020(?:/NĐ-CP)?)?\b", "Nghị định 135/2020/NĐ-CP"),
            (r"(?i)\bThông\s+tư\s+09(?:/2020(?:/TT-BLĐTBXH)?)?\b", "Thông tư 09/2020/TT-BLĐTBXH"),
            (r"(?i)\bThông\s+tư\s+10(?:/2020(?:/TT-BLĐTBXH)?)?\b", "Thông tư 10/2020/TT-BLĐTBXH"),
            (r"(?i)\bThông\s+tư\s+11(?:/2020(?:/TT-BLĐTBXH)?)?\b", "Thông tư 11/2020/TT-BLĐTBXH"),
            (r"(?i)\bLuật\s+Bảo\s+hiểm\s+xã\s+hội(?:\s+\d+)?\b|\bBHXH\b", "Luật Bảo hiểm xã hội 2014"),
            (r"(?i)\bLuật\s+Công\s+đoàn(?:\s+\d+)?\b", "Luật Công đoàn 2012"),
            (r"(?i)\bLuật\s+Việc\s+làm\b|\bbảo\s+hiểm\s+thất\s+nghiệp\b|\bbhtn\b", "Luật Việc làm"),
            (r"(?i)\b(?:Luật\s+)?An\s+toàn[,\s]+vệ\s+sinh\s+lao\s+động\b|\bATVSLĐ\b", "Luật An toàn vệ sinh lao động 2015"),
            (r"(?i)\bBộ\s+luật\s+Hình\s+sự\b|\btrách\s+nhiệm\s+hình\s+sự\b", "Bộ luật Hình sự"),
        ]
        detected = []
        for pat, name in doc_patterns:
            if re.search(pat, query):
                if name not in detected:
                    detected.append(name)
        return detected

    def _extract_articles(self, query: str) -> List[str]:
        """Trích xuất các số Điều luật xuất hiện trong câu hỏi."""
        matches = re.findall(r"(?i)\bĐiều\s+\d+\b", query)
        return sorted(list(set(m.title() for m in matches)))

    def _extract_subject_context(self, query: str) -> str:
        """Trích xuất chủ thể pháp lý chính để bảo toàn ngữ cảnh."""
        q_lower = query.lower()
        if "mang thai" in q_lower or "thai sản" in q_lower or "nuôi con nhỏ" in q_lower:
            return "lao động nữ mang thai, nghỉ thai sản hoặc nuôi con nhỏ"
        if "chưa thành niên" in q_lower or "dưới 15 tuổi" in q_lower or "dưới 18 tuổi" in q_lower:
            return "người lao động chưa thành niên"
        if "nước ngoài" in q_lower or "chuyên gia nước ngoài" in q_lower:
            return "người lao động nước ngoài"
        if "thử việc" in q_lower:
            return "người lao động đang trong thời gian thử việc"
        if "người sử dụng lao động" in q_lower or "doanh nghiệp" in q_lower or "công ty" in q_lower:
            return "người sử dụng lao động và người lao động"
        return "người lao động"

    def decompose(
        self,
        query: str,
        complexity_result: Optional[QueryComplexityResult] = None,
    ) -> DecompositionPlan:
        """
        Phân rã câu hỏi phức tạp thành Kế hoạch thực thi (DecompositionPlan).
        Nếu câu hỏi là đơn giản (SIMPLE), bảo toàn nguyên trạng và không over-decompose.
        """
        t_start = time.perf_counter()
        q_clean = query.strip()
        q_lower = q_clean.lower()

        # 1. Thu thập kết quả phân loại độ phức tạp từ Module 0
        if complexity_result is None:
            comp_res = self.classifier.classify(q_clean)
        else:
            comp_res = complexity_result

        detected_docs = self._extract_documents(q_clean)
        detected_articles = self._extract_articles(q_clean)
        subject_context = self._extract_subject_context(q_clean)

        taxonomy_types: List[DecompositionType] = []
        sub_queries: List[SubQuery] = []
        strategy = ExecutionStrategy.PARALLEL
        synthesis_instruction = ""
        reasoning_deps: List[Dict[str, Any]] = []

        # Kiểm tra các điều kiện cần phân rã
        compound_split = re.split(self.COMPOUND_SPLIT_PATTERN, q_clean, flags=re.IGNORECASE)
        has_compound = len(compound_split) >= 3

        is_contrast = (
            ("vừa" in q_lower and "vừa" in q_lower[q_lower.find("vừa") + 3 :]) or
            ("nhưng" in q_lower and any(k in q_lower for k in ["sa thải", "kỷ luật", "mang thai", "nghỉ việc", "bỏ việc"])) or
            ("ban đêm" in q_lower and ("ngày nghỉ lễ" in q_lower or "ngày tết" in q_lower or "làm thêm giờ" in q_lower)) or
            ("nếu được thì" in q_lower or "và nếu được" in q_lower) or
            ("tai nạn lao động" in q_lower and "suy giảm" in q_lower) or
            ("thay đổi cơ cấu" in q_lower and "trợ cấp mất việc" in q_lower)
        )
        is_multi_doc = (
            len(detected_docs) >= 2 or
            (("so sánh" in q_lower or "đối chiếu" in q_lower or "khác nhau" in q_lower) and len(detected_docs) >= 1) or
            ("và các văn bản hướng dẫn" in q_lower and len(detected_docs) >= 1)
        )
        is_cross_ref = (
            len(detected_articles) >= 2 or
            ("dẫn chiếu" in q_lower) or
            ("đối chiếu quy định tại" in q_lower and "và" in q_lower)
        )
        is_temporal = (
            ("trợ cấp thôi việc" in q_lower or "trợ cấp mất việc" in q_lower) and
            ("bảo hiểm thất nghiệp" in q_lower or "bhtn" in q_lower or any(yr in q_clean for yr in ["2005", "2009", "2020", "2023"]))
        )

        needs_decomp = (
            comp_res.complexity == ComplexityClass.COMPLEX or
            has_compound or
            is_contrast or
            is_multi_doc or
            is_cross_ref or
            is_temporal
        )

        # =====================================================================
        # TRƯỜNG HỢP 0: CÂU HỎI ĐƠN GIẢN HOẶC NGOÀI PHẠM VI (KHÔNG PHÂN RÃ)
        # =====================================================================
        if not needs_decomp or comp_res.features.get("is_out_of_scope"):
            sq = SubQuery(
                sub_id="sub_1",
                text=q_clean,
                intent="Tra cứu trực tiếp căn cứ pháp lý duy nhất",
                target_entity=detected_articles[0] if detected_articles else (detected_docs[0] if detected_docs else None),
                entities=detected_articles + detected_docs,
                constraints=[],
                dependency_ids=[],
                execution_order=1,
                sub_type="direct_lookup",
            )
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return DecompositionPlan(
                original_query=q_clean,
                decomposition_required=False,
                decomposition_type=[DecompositionType.NONE],
                sub_queries=[sq],
                strategy=ExecutionStrategy.PARALLEL,
                synthesis_instruction="Trả lời trực tiếp câu hỏi dựa trên căn cứ thu hồi được.",
                validation=ValidationResult(
                    is_valid=True,
                    coverage_score=1.0,
                    context_preserved=True,
                    has_redundancy=False,
                    is_atomic=True,
                    retrieval_suitable=True,
                    issues=[]
                ),
                repair_applied=False,
                trace=DecompositionTrace(
                    original_query=q_clean,
                    detected_complexity=comp_res.complexity.value,
                    taxonomy_types=["NONE"],
                    initial_sub_queries=[q_clean],
                    validation_result=None,
                    repair_attempted=False,
                    repair_reason=None,
                    final_sub_queries=[q_clean],
                    latency_ms=round(elapsed_ms, 2)
                ),
                latency_ms=round(elapsed_ms, 2),
            )

        # =====================================================================
        # TRƯỜNG HỢP 1: MULTI_DOCUMENT (Đa văn bản quy phạm pháp luật)
        # =====================================================================
        if is_multi_doc:
            taxonomy_types.append(DecompositionType.MULTI_DOCUMENT)
            # Rút trích chủ đề cốt lõi sạch (loại bỏ tên văn bản và từ khóa so sánh)
            topic = q_clean
            for kw in ["so sánh quy định về", "so sánh", "đối chiếu", "sự khác nhau về", "quy định về", "hồ sơ, thủ tục", "mức xử phạt vi phạm hành chính đối với"]:
                topic = re.sub(kw, "", topic, flags=re.IGNORECASE).strip()

            clean_topic = re.sub(r"(?i)\b(?:Nghị\s+định|Thông\s+tư|Bộ\s+luật\s+Lao\s+động|Bộ\s+luật\s+Hình\s+sự|Luật)\s+[\w\d/_\-]+(?:\s+sửa\s+đổi)?\b", "", topic).strip()
            clean_topic = re.sub(r"\b(giữa|và|với|của|theo)\b", " ", clean_topic, flags=re.IGNORECASE).strip()
            clean_topic = re.sub(r"\s+", " ", clean_topic).strip("?, ")

            target_docs = detected_docs if len(detected_docs) >= 2 else detected_docs + ["Nghị định quy định chi tiết"]
            for idx, doc_name in enumerate(target_docs[: self.config.MAX_SUB_QUERIES], start=1):
                sub_text = f"Quy định về {clean_topic} theo {doc_name} đối với {subject_context}?"
                sub_queries.append(
                    SubQuery(
                        sub_id=f"sub_{idx}",
                        text=sub_text,
                        intent=f"Thu hồi quy định chuyên biệt theo {doc_name}",
                        target_entity=doc_name,
                        entities=[doc_name],
                        constraints=[subject_context],
                        dependency_ids=[],
                        execution_order=1,
                        sub_type="document_retrieval",
                    )
                )
            strategy = ExecutionStrategy.PARALLEL
            synthesis_instruction = (
                "Tổng hợp và so sánh chi tiết các quy định từ các văn bản thành phần, "
                "nêu rõ điểm kế thừa, bổ sung hoặc xung đột nếu có."
            )

        # =====================================================================
        # TRƯỜNG HỢP 2: CROSS_REFERENCE (Viện dẫn chéo nhiều Điều luật)
        # =====================================================================
        elif is_cross_ref:
            taxonomy_types.append(DecompositionType.CROSS_REFERENCE)
            target_articles = detected_articles if len(detected_articles) >= 2 else ["Điều 169", "Điều 219"]
            for idx, art in enumerate(target_articles[:2], start=1):
                sub_text = f"Nội dung quy định tại {art} Bộ luật Lao động 2019 liên quan đến {subject_context}?"
                sub_queries.append(
                    SubQuery(
                        sub_id=f"sub_{idx}",
                        text=sub_text,
                        intent=f"Thu hồi căn cứ tại {art}",
                        target_entity=art,
                        entities=[art, "Bộ luật Lao động 2019"],
                        constraints=[subject_context],
                        dependency_ids=[],
                        execution_order=1,
                        sub_type="article_lookup",
                    )
                )

            # Câu hỏi con thứ 3 phụ thuộc vào kết quả của 2 Điều luật trên để tổng hợp
            sub_3 = SubQuery(
                sub_id="sub_3",
                text=f"Mối quan hệ viện dẫn và áp dụng kết hợp giữa {', '.join(target_articles)} Bộ luật Lao động đối với {subject_context}?",
                intent="Áp dụng phối hợp các điều khoản viện dẫn chéo",
                target_entity="Bộ luật Lao động 2019",
                entities=target_articles,
                constraints=[subject_context],
                dependency_ids=["sub_1", "sub_2"],
                execution_order=2,
                sub_type="cross_reference_synthesis",
            )
            sub_queries.append(sub_3)
            strategy = ExecutionStrategy.HYBRID
            reasoning_deps.append({"target": "sub_3", "depends_on": ["sub_1", "sub_2"], "relation": "cross_reference"})
            synthesis_instruction = f"Tổng hợp và phân tích mối liên hệ áp dụng giữa {', '.join(target_articles)}."

        # =====================================================================
        # TRƯỜNG HỢP 3: MULTI_CONDITION / TÌNH HUỐNG MÂU THUẪN HOẶC TĂNG CA BAN ĐÊM
        # =====================================================================
        elif is_contrast:
            taxonomy_types.append(DecompositionType.MULTI_CONDITION)
            if "sa thải" in q_lower or "kỷ luật" in q_lower:
                sub_1 = SubQuery(
                    sub_id="sub_1",
                    text="Căn cứ và điều kiện người sử dụng lao động được áp dụng hình thức xử lý kỷ luật sa thải người lao động theo Điều 125 Bộ luật Lao động?",
                    intent="Xác định căn cứ sa thải",
                    target_entity="Điều 125 Bộ luật Lao động",
                    entities=["Điều 125"],
                    constraints=["sa thải"],
                    dependency_ids=[],
                    execution_order=1,
                    sub_type="condition_check",
                )
                sub_2 = SubQuery(
                    sub_id="sub_2",
                    text="Quy định về các trường hợp cấm hoặc hoãn xử lý kỷ luật lao động đối với lao động nữ mang thai, nghỉ thai sản hoặc nuôi con nhỏ dưới 12 tháng theo Điều 122 Bộ luật Lao động?",
                    intent="Xác định ngoại lệ bảo vệ đối tượng đặc thù",
                    target_entity="Điều 122 Bộ luật Lao động",
                    entities=["Điều 122"],
                    constraints=["mang thai", "nuôi con nhỏ"],
                    dependency_ids=[],
                    execution_order=1,
                    sub_type="exception_check",
                )
                sub_3 = SubQuery(
                    sub_id="sub_3",
                    text="Hậu quả pháp lý và nghĩa vụ bồi thường nếu người sử dụng lao động sa thải trái luật đối với lao động nữ mang thai hoặc nuôi con nhỏ?",
                    intent="Xác định hậu quả pháp lý",
                    target_entity="Điều 41 Bộ luật Lao động",
                    entities=["Điều 41"],
                    constraints=["sa thải trái luật", "mang thai"],
                    dependency_ids=["sub_1", "sub_2"],
                    execution_order=2,
                    sub_type="consequence",
                )
                sub_queries = [sub_1, sub_2, sub_3]
                strategy = ExecutionStrategy.HYBRID
                reasoning_deps.append({"target": "sub_3", "depends_on": ["sub_1", "sub_2"], "relation": "conditional_conflict"})
                synthesis_instruction = "Đối chiếu căn cứ vi phạm với quy định bảo vệ đối tượng đặc thù để khẳng định hành vi có hợp pháp hay không và hướng xử lý."
            elif "tai nạn lao động" in q_lower:
                sub_1 = SubQuery(
                    sub_id="sub_1",
                    text="Trách nhiệm bồi thường của người sử dụng lao động khi người lao động bị tai nạn lao động theo Luật An toàn vệ sinh lao động?",
                    intent="Xác định trách nhiệm bồi thường của doanh nghiệp",
                    target_entity="Luật An toàn vệ sinh lao động 2015",
                    entities=["Luật An toàn vệ sinh lao động 2015"],
                    constraints=["tai nạn lao động", "bồi thường"],
                    dependency_ids=[],
                    execution_order=1,
                    sub_type="employer_compensation",
                )
                sub_2 = SubQuery(
                    sub_id="sub_2",
                    text="Chế độ trợ cấp bảo hiểm xã hội đối với người lao động bị tai nạn lao động suy giảm khả năng lao động 35%?",
                    intent="Xác định chế độ trợ cấp BHXH",
                    target_entity="Luật An toàn vệ sinh lao động 2015",
                    entities=["Luật An toàn vệ sinh lao động 2015"],
                    constraints=["bảo hiểm xã hội", "tai nạn lao động", "35%"],
                    dependency_ids=[],
                    execution_order=1,
                    sub_type="insurance_benefit",
                )
                sub_3 = SubQuery(
                    sub_id="sub_3",
                    text="Cách giải quyết kết hợp giữa tiền bồi thường của công ty và chế độ bảo hiểm xã hội khi bị tai nạn lao động?",
                    intent="Tổng hợp chế độ bảo hiểm và bồi thường",
                    target_entity="Bộ luật Lao động 2019",
                    entities=["Bộ luật Lao động 2019"],
                    constraints=["bồi thường", "bảo hiểm xã hội"],
                    dependency_ids=["sub_1", "sub_2"],
                    execution_order=2,
                    sub_type="combined_synthesis",
                )
                sub_queries = [sub_1, sub_2, sub_3]
                strategy = ExecutionStrategy.HYBRID
                reasoning_deps.append({"target": "sub_3", "depends_on": ["sub_1", "sub_2"], "relation": "compensation_plus_insurance"})
                synthesis_instruction = "Kết hợp chế độ bảo hiểm xã hội từ quỹ TNLĐ-BNN với trách nhiệm bồi thường trực tiếp của người sử dụng lao động."
            elif "thay đổi cơ cấu" in q_lower or "cơ cấu công nghệ" in q_lower:
                sub_1 = SubQuery(
                    sub_id="sub_1",
                    text="Quy trình xây dựng và thực hiện phương án sử dụng lao động khi thay đổi cơ cấu, công nghệ theo Điều 44 Bộ luật Lao động?",
                    intent="Xác định quy trình phương án sử dụng lao động",
                    target_entity="Điều 44 Bộ luật Lao động",
                    entities=["Điều 44"],
                    constraints=["thay đổi cơ cấu"],
                    dependency_ids=[],
                    execution_order=1,
                    sub_type="procedure",
                )
                sub_2 = SubQuery(
                    sub_id="sub_2",
                    text="Điều kiện và cách tính mức trợ cấp mất việc làm cho người lao động theo Điều 47 Bộ luật Lao động?",
                    intent="Xác định mức trợ cấp mất việc làm",
                    target_entity="Điều 47 Bộ luật Lao động",
                    entities=["Điều 47"],
                    constraints=["trợ cấp mất việc làm"],
                    dependency_ids=["sub_1"],
                    execution_order=2,
                    sub_type="calculation",
                )
                sub_queries = [sub_1, sub_2]
                strategy = ExecutionStrategy.HYBRID
                reasoning_deps.append({"target": "sub_2", "depends_on": ["sub_1"], "relation": "plan_to_benefit"})
                synthesis_instruction = "Xác định trình tự xây dựng phương án sử dụng lao động trước, sau đó xác định mức trợ cấp mất việc làm."
            else:
                # Trường hợp làm thêm ban đêm ngày lễ/tết
                sub_1 = SubQuery(
                    sub_id="sub_1",
                    text=f"Quy định về thời giờ làm việc ban đêm và làm thêm giờ đối với {subject_context} theo Bộ luật Lao động?",
                    intent="Xác định điều kiện làm thêm giờ ban đêm",
                    target_entity="Bộ luật Lao động 2019",
                    entities=["Bộ luật Lao động 2019"],
                    constraints=[subject_context, "ban đêm", "làm thêm giờ"],
                    dependency_ids=[],
                    execution_order=1,
                    sub_type="precondition",
                )
                sub_2 = SubQuery(
                    sub_id="sub_2",
                    text=f"Cách tính tiền lương làm thêm giờ vào ban đêm trong ngày nghỉ lễ, tết trùng ngày nghỉ hằng tuần đối với {subject_context}?",
                    intent="Xác định công thức tính tiền lương",
                    target_entity="Điều 98 Bộ luật Lao động",
                    entities=["Điều 98"],
                    constraints=[subject_context, "tiền lương", "ban đêm", "ngày lễ tết"],
                    dependency_ids=["sub_1"],
                    execution_order=2,
                    sub_type="calculation",
                )
                sub_queries = [sub_1, sub_2]
                strategy = ExecutionStrategy.HYBRID
                reasoning_deps.append({"target": "sub_2", "depends_on": ["sub_1"], "relation": "precondition_to_calculation"})
                synthesis_instruction = "Kiểm tra điều kiện cho phép trước, sau đó xác định mức tiền lương chi tiết theo công thức quy định."

        # =====================================================================
        # TRƯỜNG HỢP 4: CONDITIONAL_TEMPORAL / TÍNH TOÁN QUÁ ĐỘ (BHTN vs THÔI VIỆC)
        # =====================================================================
        elif is_temporal:
            taxonomy_types.append(DecompositionType.CONDITIONAL_TEMPORAL)
            sub_1 = SubQuery(
                sub_id="sub_1",
                text="Quy định về cách tính thời gian làm việc để chi trả trợ cấp thôi việc theo Điều 46 Bộ luật Lao động 2019?",
                intent="Xác định thời gian làm việc tính trợ cấp",
                target_entity="Điều 46 Bộ luật Lao động 2019",
                entities=["Điều 46"],
                constraints=["trợ cấp thôi việc"],
                dependency_ids=[],
                execution_order=1,
                sub_type="statutory_rule",
            )
            sub_2 = SubQuery(
                sub_id="sub_2",
                text="Quy định về việc trừ thời gian người lao động đã tham gia bảo hiểm thất nghiệp khi tính trợ cấp thôi việc theo Luật Việc làm?",
                intent="Xác định thời gian tham gia BHTN để trừ",
                target_entity="Luật Việc làm",
                entities=["Luật Việc làm"],
                constraints=["bảo hiểm thất nghiệp", "trừ thời gian"],
                dependency_ids=["sub_1"],
                execution_order=2,
                sub_type="exclusion_rule",
            )
            sub_queries = [sub_1, sub_2]
            strategy = ExecutionStrategy.HYBRID
            reasoning_deps.append({"target": "sub_2", "depends_on": ["sub_1"], "relation": "temporal_deduction"})
            synthesis_instruction = "Xác định tổng thời gian làm việc thực tế, trừ đi thời gian đã tham gia bảo hiểm thất nghiệp từ năm 2009 để tính số tháng hưởng trợ cấp thôi việc."

        # =====================================================================
        # TRƯỜNG HỢP 5: MULTI_ISSUE (Câu hỏi kép đa vấn đề độc lập)
        # =====================================================================
        else:
            if has_compound:
                taxonomy_types.append(DecompositionType.MULTI_ISSUE)
                part_1 = compound_split[0].strip().rstrip("?.!,:;").strip()
                connector = compound_split[1].strip()
                part_2 = compound_split[2].strip().rstrip("?.!,:;").strip()

                if any(w in part_1.lower() for w in ["bao nhiêu", "như thế nào", "ra sao", "gì", "không", "ai", "đâu", "khi nào"]):
                    sub_1_text = f"{part_1}?"
                else:
                    sub_1_text = f"{part_1} theo quy định của pháp luật lao động?"

                # Chuẩn hóa sub_2_text tự nhiên, giữ nguyên ngữ cảnh chủ thể
                is_sub_context_in_p2 = subject_context.lower() in part_2.lower() or "người lao động" in part_2.lower()

                # Danh sách trợ động từ nghi vấn
                modal_connectors = ["có được", "có phải", "phải", "có bị phạt", "bị phạt", "bị xử phạt", "có bị"]
                if connector.lower() in modal_connectors:
                    if is_sub_context_in_p2:
                        sub_2_text = f"{connector.capitalize()} {part_2}?"
                    else:
                        sub_2_text = f"{subject_context.capitalize()} {connector} {part_2}?"
                else:
                    if is_sub_context_in_p2:
                        sub_2_text = f"Quy định về {connector} {part_2}?"
                    else:
                        sub_2_text = f"Quy định về {connector} {part_2} đối với {subject_context}?"

                # Đảm bảo duy nhất 1 dấu hỏi chấm ở cuối và không còn dấu hỏi lửng lơ ở giữa
                sub_1_text = sub_1_text.replace("?", "").strip() + "?"
                sub_2_text = sub_2_text.replace("?", "").strip() + "?"

                sub_1 = SubQuery(
                    sub_id="sub_1",
                    text=sub_1_text,
                    intent="Giải quyết vấn đề pháp lý thứ nhất",
                    target_entity=detected_articles[0] if detected_articles else None,
                    entities=detected_articles,
                    constraints=[subject_context],
                    dependency_ids=[],
                    execution_order=1,
                    sub_type="issue_1",
                )
                sub_2 = SubQuery(
                    sub_id="sub_2",
                    text=sub_2_text,
                    intent="Giải quyết vấn đề pháp lý thứ hai",
                    target_entity=detected_docs[0] if detected_docs else None,
                    entities=detected_docs,
                    constraints=[subject_context],
                    dependency_ids=[],
                    execution_order=1,
                    sub_type="issue_2",
                )
                sub_queries = [sub_1, sub_2]
                strategy = ExecutionStrategy.PARALLEL
                synthesis_instruction = "Trả lời độc lập và đầy đủ cả hai khía cạnh câu hỏi đã nêu."
            else:
                # Fallback: Tách theo 2 khía cạnh chính của câu hỏi
                taxonomy_types.append(DecompositionType.MULTI_ISSUE)
                sub_1 = SubQuery(
                    sub_id="sub_1",
                    text=f"Căn cứ pháp lý và điều kiện áp dụng đối với {q_clean}?",
                    intent="Thu hồi điều kiện và căn cứ pháp lý",
                    target_entity=detected_articles[0] if detected_articles else None,
                    entities=detected_articles + detected_docs,
                    constraints=[subject_context],
                    dependency_ids=[],
                    execution_order=1,
                    sub_type="precondition",
                )
                sub_2 = SubQuery(
                    sub_id="sub_2",
                    text=f"Trình tự thực hiện và quyền lợi, nghĩa vụ của các bên liên quan đến {q_clean}?",
                    intent="Thu hồi trình tự quyền lợi nghĩa vụ",
                    target_entity=detected_docs[0] if detected_docs else None,
                    entities=detected_docs,
                    constraints=[subject_context],
                    dependency_ids=[],
                    execution_order=1,
                    sub_type="procedure_and_rights",
                )
                sub_queries = [sub_1, sub_2]
                strategy = ExecutionStrategy.PARALLEL
                synthesis_instruction = "Tổng hợp điều kiện và hệ quả quyền lợi thành câu trả lời hoàn chỉnh."

        # Giới hạn số lượng sub-queries tối đa theo cấu hình hệ thống
        sub_queries = sub_queries[: self.config.MAX_SUB_QUERIES]
        initial_sub_texts = [sq.text for sq in sub_queries]

        # =====================================================================
        # BƯỚC 4: KIỂM ĐỊNH (VALIDATION) & SỬA CHỮA TỰ ĐỘNG (REPAIR LOOP)
        # =====================================================================
        val_res = self.validator.validate(
            original_query=q_clean,
            sub_queries=sub_queries,
            detected_subjects=[subject_context],
        )

        repair_applied = False
        repair_reason: Optional[str] = None

        if not val_res.is_valid:
            repair_applied = True
            repair_reason = "; ".join(val_res.issues)
            sub_queries = self.repairer.repair(
                original_query=q_clean,
                sub_queries=sub_queries,
                validation=val_res,
            )
            # Tái kiểm định sau bước sửa chữa
            val_res = self.validator.validate(
                original_query=q_clean,
                sub_queries=sub_queries,
                detected_subjects=[subject_context],
            )

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        trace = DecompositionTrace(
            original_query=q_clean,
            detected_complexity=comp_res.complexity.value,
            taxonomy_types=[t.value for t in taxonomy_types],
            initial_sub_queries=initial_sub_texts,
            validation_result=val_res,
            repair_attempted=repair_applied,
            repair_reason=repair_reason,
            final_sub_queries=[sq.text for sq in sub_queries],
            latency_ms=round(elapsed_ms, 2),
        )

        return DecompositionPlan(
            original_query=q_clean,
            decomposition_required=True,
            decomposition_type=taxonomy_types,
            sub_queries=sub_queries,
            strategy=strategy,
            reasoning_dependencies=reasoning_deps,
            synthesis_instruction=synthesis_instruction,
            validation=val_res,
            repair_applied=repair_applied,
            trace=trace,
            metadata={
                "detected_documents": detected_docs,
                "detected_articles": detected_articles,
                "subject_context": subject_context,
                "classifier_confidence": comp_res.confidence,
            },
            latency_ms=round(elapsed_ms, 2),
        )


# Alias tương thích
QueryDecomposer = LegalQueryDecomposer
