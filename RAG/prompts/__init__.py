"""RAG/prompts/__init__.py - Export prompt templates and instructions."""

from RAG.prompts.legal_prompts import (
    SYSTEM_PROMPT_CONSERVATIVE_LEGAL,
    USER_PROMPT_TEMPLATE,
    STANDARD_REFUSAL_ANSWER,
)

__all__ = [
    "SYSTEM_PROMPT_CONSERVATIVE_LEGAL",
    "USER_PROMPT_TEMPLATE",
    "STANDARD_REFUSAL_ANSWER",
]
