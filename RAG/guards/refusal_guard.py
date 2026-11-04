"""refusal_guard.py - Chốt chặn an toàn, cơ chế từ chối (Refusal Guard) và kiểm chứng ảo giác (Hallucination Verifier).

Đảm bảo an toàn 3 tầng:
1. Pre-generation Guard: Chặn trước khi gọi LLM nếu retrieval rỗng hoặc độ tương đồng quá thấp.
2. Post-generation Citation Guard: Kiểm tra tính hợp lệ của trích dẫn và tính nhất quán của trạng thái từ chối.
3. Post-generation Faithfulness Guard: Kiểm chứng tính trung thực thời gian thực (Self-Reflection / Faithfulness Gate), phát hiện và chặn đứng ảo giác (hallucination).
"""

from __future__ import annotations
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from RAG.retriever.schema import RetrievedChunk
from RAG.generator.schema import GenerationResult
from RAG.citation.schema import CitationResolutionResult
from RAG.guards.config import GuardConfig, default_guard_config
from RAG.guards.hallucination_verifier import RealTimeHallucinationVerifier, FaithfulnessVerificationReport

logger = logging.getLogger(__name__)


class GuardCheckResult(BaseModel):
    """Kết quả kiểm tra từ chốt chặn an toàn (Guard Check)."""

    passed: bool = Field(..., description="True nếu vượt qua kiểm tra an toàn, False nếu bị chặn")
    trigger_refusal: bool = Field(default=False, description="True nếu cần kích hoạt từ chối (refused=True)")
    reason: Optional[str] = Field(default=None, description="Lý do kích hoạt từ chối hoặc bị chặn")
    refusal_message: Optional[str] = Field(default=None, description="Chuỗi thông báo từ chối chuẩn mực")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Các chỉ số đánh giá đi kèm")


class RefusalGuard:
    """Lớp quản lý chốt chặn an toàn và cơ chế từ chối của hệ thống RAG."""

    def __init__(
        self,
        config: Optional[GuardConfig] = None,
        hallucination_verifier: Optional[RealTimeHallucinationVerifier] = None,
    ):
        self.config = config or default_guard_config
        self.hallucination_verifier = hallucination_verifier or RealTimeHallucinationVerifier()

    def check_pre_generation(self, retrieved_chunks: List[RetrievedChunk]) -> GuardCheckResult:
        """Kiểm tra chốt chặn an toàn TRƯỚC KHI sinh câu trả lời bằng LLM.
        
        Args:
            retrieved_chunks: Danh sách các đoạn luật thu hồi từ RAG-03.
            
        Returns:
            GuardCheckResult.
        """
        if not self.config.ENABLE_PRE_GENERATION_GUARD:
            return GuardCheckResult(passed=True, trigger_refusal=False)

        # 1. Kiểm tra danh sách rỗng
        if not retrieved_chunks or len(retrieved_chunks) < self.config.MIN_RETRIEVED_CHUNKS:
            logger.info("Pre-generation Guard: Danh sách retrieved_chunks rỗng. Kích hoạt từ chối sớm.")
            return GuardCheckResult(
                passed=False,
                trigger_refusal=True,
                reason="Không tìm thấy bất kỳ tài liệu pháp lý nào phù hợp từ bộ thu hồi.",
                refusal_message=self.config.REFUSAL_MESSAGE,
                metrics={"retrieved_count": 0, "max_score": 0.0}
            )

        # 2. Kiểm tra ngưỡng tương đồng cao nhất (max similarity score)
        max_score = max(chunk.score for chunk in retrieved_chunks)
        if max_score < self.config.SIMILARITY_THRESHOLD:
            logger.info(
                "Pre-generation Guard: Điểm tương đồng cao nhất (%.4f) thấp hơn ngưỡng tối thiểu (%.4f). Kích hoạt từ chối sớm.",
                max_score,
                self.config.SIMILARITY_THRESHOLD
            )
            return GuardCheckResult(
                passed=False,
                trigger_refusal=True,
                reason=(
                    f"Độ tương đồng ngữ nghĩa cao nhất ({max_score:.4f}) thấp hơn ngưỡng cho phép "
                    f"({self.config.SIMILARITY_THRESHOLD:.4f}). Bằng chứng không đủ độ tin cậy để trả lời."
                ),
                refusal_message=self.config.REFUSAL_MESSAGE,
                metrics={"retrieved_count": len(retrieved_chunks), "max_score": max_score}
            )

        # Đạt yêu cầu -> Cho phép chuyển tiếp sang Context Builder và Generator
        return GuardCheckResult(
            passed=True,
            trigger_refusal=False,
            metrics={"retrieved_count": len(retrieved_chunks), "max_score": max_score}
        )

    def check_post_generation(
        self,
        generation_result: GenerationResult,
        citation_result: CitationResolutionResult,
        context_text: Optional[str] = None,
    ) -> GuardCheckResult:
        """Kiểm tra chốt chặn an toàn SAU KHI sinh câu trả lời bằng LLM.
        
        Args:
            generation_result: Kết quả sinh từ Generator (RAG-05).
            citation_result: Kết quả phân giải trích dẫn từ CitationResolver (RAG-06).
            context_text: Toàn bộ ngữ cảnh tài liệu pháp luật cung cấp cho LLM (dùng để kiểm chứng ảo giác).
            
        Returns:
            GuardCheckResult.
        """
        if not self.config.ENABLE_POST_GENERATION_GUARD:
            return GuardCheckResult(passed=True, trigger_refusal=False)

        # Nếu bản thân generator đã tự từ chối -> Đồng thuận
        if generation_result.refused:
            return GuardCheckResult(
                passed=True,
                trigger_refusal=True,
                reason=generation_result.reason or "Generator đã từ chối hợp lệ do thiếu căn cứ.",
                refusal_message=self.config.REFUSAL_MESSAGE
            )

        # Nếu generator đưa ra câu trả lời nhưng 100% trích dẫn là invalid (nguồn bịa đặt, VD [SOURCE 99])
        if self.config.REJECT_UNSUPPORTED_ANSWERS:
            if citation_result.has_invalid_citations and len(citation_result.valid_citations) == 0:
                logger.warning(
                    "Post-generation Guard: Toàn bộ trích dẫn của LLM đều không hợp lệ (%s). Cưỡng chế từ chối.",
                    citation_result.invalid_citations
                )
                return GuardCheckResult(
                    passed=False,
                    trigger_refusal=True,
                    reason="Tất cả các trích dẫn trong câu trả lời đều không tồn tại trong tài liệu được cung cấp (REJECT INVALID CITATIONS).",
                    refusal_message=self.config.REFUSAL_MESSAGE,
                    metrics={"invalid_citations": citation_result.invalid_citations}
                )

        # Kiểm chứng tính trung thực và phát hiện ảo giác (Real-time Hallucination Verifier)
        faith_metrics: Dict[str, Any] = {
            "valid_citations_count": citation_result.citations_count,
            "has_invalid_citations": citation_result.has_invalid_citations
        }

        if context_text and not generation_result.refused:
            faith_report: FaithfulnessVerificationReport = self.hallucination_verifier.verify(
                answer=generation_result.answer,
                context=context_text,
            )
            faith_metrics.update({
                "faithfulness_score": faith_report.faithfulness_score,
                "hallucination_detected": faith_report.hallucination_detected,
                "contradicted_count": faith_report.contradicted_count,
                "unsupported_count": faith_report.unsupported_count,
                "action_taken": faith_report.action_taken,
            })

            # Nếu phát hiện ảo giác nghiêm trọng (bịa đặt số điều luật hoặc tỷ lệ trung thực quá thấp)
            if not faith_report.passed:
                logger.warning(
                    "Post-generation Guard: Phát hiện ảo giác câu trả lời (%s). Cưỡng chế từ chối.",
                    faith_report.reason
                )
                return GuardCheckResult(
                    passed=False,
                    trigger_refusal=True,
                    reason=faith_report.reason,
                    refusal_message=self.config.REFUSAL_MESSAGE,
                    metrics=faith_metrics,
                )

        return GuardCheckResult(
            passed=True,
            trigger_refusal=False,
            metrics=faith_metrics,
        )

    def create_refusal_response(
        self,
        reason: str,
        model_name: str = "refusal-guard",
        provider: str = "guard"
    ) -> GenerationResult:
        """Tạo đối tượng GenerationResult phản ánh trạng thái từ chối chuẩn mực mà không cần gọi LLM."""
        return GenerationResult(
            answer=self.config.REFUSAL_MESSAGE,
            citations=[],
            refused=True,
            reason=reason,
            raw_response=None,
            model_name=model_name,
            provider=provider,
            latency_ms=0.0
        )
