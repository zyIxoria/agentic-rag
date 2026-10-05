"""gemini_generator.py - Triển khai Generator sử dụng Google Gemini REST API."""

from __future__ import annotations
import os
import time
import logging
from typing import Optional
import requests

from RAG.generator.base import BaseLegalGenerator
from RAG.generator.schema import GenerationRequest, GenerationResult
from RAG.generator.parser import parse_generator_output
from RAG.prompts.legal_prompts import SYSTEM_PROMPT_CONSERVATIVE_LEGAL, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class GeminiLegalGenerator(BaseLegalGenerator):
    """Bộ sinh câu trả lời sử dụng Google Gemini qua REST API với Structured JSON Mode."""

    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        api_key: Optional[str] = None,
        timeout_seconds: int = 30
    ):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            logger.warning("GEMINI_API_KEY chưa được thiết lập. Các lệnh gọi API Gemini sẽ bị từ chối.")

    def generate_structured(self, request: GenerationRequest) -> GenerationResult:
        """Thực hiện gọi Google Gemini REST API sinh câu trả lời."""
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY không được cung cấp hoặc rỗng. Hãy thiết lập biến môi trường GEMINI_API_KEY."
            )

        start_time = time.perf_counter()

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        user_content = USER_PROMPT_TEMPLATE.format(
            context=request.context,
            question=request.question
        )

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT_CONSERVATIVE_LEGAL}]
            },
            "contents": [
                {
                    "parts": [{"text": user_content}]
                }
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
                "response_mime_type": "application/json"
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout_seconds)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if resp.status_code != 200:
                raise RuntimeError(
                    f"Gemini API trả về mã lỗi HTTP {resp.status_code}: {resp.text}"
                )

            data = resp.json()
            raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = parse_generator_output(raw_content)

            return GenerationResult(
                answer=parsed.answer,
                citations=parsed.citations,
                refused=parsed.refused,
                reason=parsed.reason,
                raw_response=raw_content,
                model_name=self.model_name,
                provider="gemini",
                latency_ms=round(elapsed_ms, 2)
            )

        except requests.exceptions.RequestException as req_err:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("Lỗi kết nối mạng tới Gemini API: %s", req_err)
            raise RuntimeError(f"Lỗi kết nối Gemini API: {req_err}") from req_err
