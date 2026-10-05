"""
CRAG Query Transformation Package.
"""

from CRAG.transformation.schema import TransformedQuery
from CRAG.transformation.query_rewriter import LegalQueryRewriter

__all__ = ["TransformedQuery", "LegalQueryRewriter"]
