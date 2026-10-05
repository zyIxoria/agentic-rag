"""openai_generator.py - Triển khai Generator sử dụng OpenAI API (mặc định gpt-4o-mini)."""

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


class OpenAILegalGenerator(BaseLegalGenerator):
    """Bộ sinh câu trả lời sử dụng mô hình OpenAI qua REST API với Structured JSON Mode."""

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: int = 30
    ):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            logger.warning("OPENAI_API_KEY chưa được thiết lập. Các lệnh gọi API OpenAI sẽ bị từ chối.")

    def generate_structured(self, request: GenerationRequest) -> GenerationResult:
        """Thực hiện gọi API OpenAI sinh câu trả lời."""
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY không được cung cấp hoặc rỗng. Hãy thiết lập biến môi trường OPENAI_API_KEY."
            )

        start_time = time.perf_counter()

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        user_content = USER_PROMPT_TEMPLATE.format(
            context=request.context,
            question=request.question
        )

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_CONSERVATIVE_LEGAL},
                {"role": "user", "content": user_content}
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "response_format": {"type": "json_object"}
        }

        try:
            resp = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if resp.status_code != 200:
                err_detail = resp.text
                try:
                    err_json = resp.json()
                    err_detail = err_json.get("error", {}).get("message", resp.text)
                except Exception:
                    pass
                raise RuntimeError(
                    f"OpenAI API trả về mã lỗi HTTP {resp.status_code}: {err_detail}"
                )

            data = resp.json()
            raw_content = data["choices"][0]["message"]["content"]
            parsed = parse_generator_output(raw_content)

            return GenerationResult(
                answer=parsed.answer,
                citations=parsed.citations,
                refused=parsed.refused,
                reason=parsed.reason,
                raw_response=raw_content,
                model_name=self.model_name,
                provider="openai",
                latency_ms=round(elapsed_ms, 2)
            )

        except requests.exceptions.RequestException as req_err:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("Lỗi kết nối mạng tới OpenAI API: %s", req_err)
            raise RuntimeError(f"Lỗi kết nối OpenAI API: {req_err}") from req_err
