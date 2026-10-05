"""
CRAG Knowledge Refinement Package.
Bao gồm các cơ chế bóc tách dải tri thức (Stripper) và tái hợp ngữ cảnh (Recomposer).
"""

from CRAG.refinement.schema import (
    KnowledgeStrip,
    RefinedDocument,
    RefinedContext,
)
from CRAG.refinement.stripper import KnowledgeStripper
from CRAG.refinement.recomposer import KnowledgeRecomposer

__all__ = [
    "KnowledgeStrip",
    "RefinedDocument",
    "RefinedContext",
    "KnowledgeStripper",
    "KnowledgeRecomposer",
]
