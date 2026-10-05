"""
CRAG Search Package.
"""

from CRAG.search.schema import WebSearchResult, SearchResponse
from CRAG.search.base import BaseWebSearcher
from CRAG.search.mock_searcher import MockLegalWebSearcher
from CRAG.search.web_searcher import LegalWebSearcher

__all__ = [
    "WebSearchResult",
    "SearchResponse",
    "BaseWebSearcher",
    "MockLegalWebSearcher",
    "LegalWebSearcher",
]
