"""RAG/generator/__init__.py - Phân hệ sinh câu trả lời Traditional RAG (RAG-05)."""

from RAG.generator.schema import LegalAnswer, GenerationRequest, GenerationResult
from RAG.generator.parser import parse_generator_output
from RAG.generator.base import BaseLegalGenerator
from RAG.generator.openai_generator import OpenAILegalGenerator
from RAG.generator.gemini_generator import GeminiLegalGenerator
from RAG.generator.mock_generator import MockLegalGenerator
from RAG.generator.factory import get_generator

__all__ = [
    "LegalAnswer",
    "GenerationRequest",
    "GenerationResult",
    "parse_generator_output",
    "BaseLegalGenerator",
    "OpenAILegalGenerator",
    "GeminiLegalGenerator",
    "MockLegalGenerator",
    "get_generator",
]
