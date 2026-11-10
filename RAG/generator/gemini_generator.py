"""gemini_generator.py - Triển khai Generator sử dụng Google Gemini REST API."""

from __future__ import annotations
import os
import random
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
    """Bộ sinh câu trả lời sử dụng Google Gemini qua REST API với Structured JSON Mode và cơ chế Retry tự động."""

    def __init__(
        self,
        model_name: str = "gemini-3.5-flash-lite",
        api_key: Optional[str] = None,
        timeout_seconds: int = 35,
        max_retries: int = 3
    ):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        if not self.api_key:
            logger.warning("GEMINI_API_KEY chưa được thiết lập. Các lệnh gọi API Gemini sẽ bị từ chối.")

    def generate_structured(self, request: GenerationRequest) -> GenerationResult:
        """Thực hiện gọi Google Gemini REST API sinh câu trả lời kèm retry khi gặp rate-limit hoặc 503."""
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

        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(url, json=payload, timeout=self.timeout_seconds)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise RuntimeError("Gemini API không trả về candidate nào.")

                    raw_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    parsed = parse_generator_output(raw_content)

                    usage = data.get("usageMetadata", {})
                    inp_tok = usage.get("promptTokenCount", len(user_content) // 4)
                    out_tok = usage.get("candidatesTokenCount", len(raw_content) // 4)

                    return GenerationResult(
                        answer=parsed.answer,
                        citations=parsed.citations,
                        refused=parsed.refused,
                        reason=parsed.reason,
                        raw_response=raw_content,
                        model_name=self.model_name,
                        provider="gemini",
                        latency_ms=round(elapsed_ms, 2),
                        input_tokens=inp_tok,
                        output_tokens=out_tok,
                    )

                elif resp.status_code in (429, 503):
                    wait_time = (2 ** attempt) + random.uniform(1.0, 2.5)
                    logger.warning(
                        "Gemini API báo %d (%s), đang chờ %.1fs trước khi thử lại (lần %d/%d)...",
                        resp.status_code, resp.reason, wait_time, attempt + 1, self.max_retries
                    )
                    time.sleep(wait_time)
                    continue

                else:
                    err_msg = resp.text
                    try:
                        err_json = resp.json()
                        err_msg = err_json.get("error", {}).get("message", resp.text)
                    except Exception:
                        pass
                    if resp.status_code == 402:
                        raise RuntimeError(
                            f"Gemini API báo lỗi 402 (Hết số dư tín dụng dự án): {err_msg}."
                        )
                    last_error = f"HTTP {resp.status_code}: {err_msg}"

            except requests.exceptions.RequestException as req_err:
                last_error = str(req_err)
                wait_time = (2 ** attempt) + random.uniform(1.0, 2.0)
                logger.warning("Lỗi kết nối Gemini: %s, chờ %.1fs...", req_err, wait_time)
                time.sleep(wait_time)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        raise RuntimeError(f"Gemini API thất bại sau {self.max_retries + 1} lần thử: {last_error}")
