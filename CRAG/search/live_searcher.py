"""
Live Legal Web Searcher for CRAG Framework.
Tích hợp Live Web Search Engine thực tế (DuckDuckGo Search qua ddgs, hỗ trợ Serper/Tavily)
với cơ chế lọc và ưu tiên các cổng thông tin pháp luật Việt Nam.
"""

import time
import os
import json
import logging
import urllib.request
import urllib.parse
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from CRAG.search.base import BaseWebSearcher
from CRAG.search.schema import SearchResponse, WebSearchResult

logger = logging.getLogger(__name__)

# Danh sách tên miền pháp luật và cơ quan nhà nước uy tín tại Việt Nam
TRUSTED_LEGAL_DOMAINS = {
    "thuvienphapluat.vn": "Thư Viện Pháp Luật",
    "luatvietnam.vn": "Luật Việt Nam",
    "molisa.gov.vn": "Bộ Lao động - Thương binh và Xã hội",
    "moj.gov.vn": "Bộ Tư Pháp",
    "chinhphu.vn": "Cổng TTĐT Chính Phủ",
    "baohiemxahoi.gov.vn": "Bảo Hiểm Xã Hội Việt Nam",
    "congbao.chinhphu.vn": "Công Báo Nước CHXHCN Việt Nam",
    "vbpl.vn": "Cơ Sở Dữ Liệu Quốc Gia Về VBPL",
}


class LiveLegalWebSearcher(BaseWebSearcher):
    """
    Searcher kết nối Live Web thực tế cho hệ thống CRAG.
    Ưu tiên DuckDuckGo (không yêu cầu API key), hỗ trợ Serper hoặc Tavily nếu có API key trong môi trường.
    """

    def __init__(self, provider: str = "duckduckgo", timeout_sec: float = 6.0):
        self.provider = provider.lower()
        self.timeout_sec = timeout_sec

    def _get_source_name(self, url: str) -> str:
        """Nhận diện nguồn trích dẫn từ URL."""
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            for trusted_domain, name in TRUSTED_LEGAL_DOMAINS.items():
                if domain == trusted_domain or domain.endswith("." + trusted_domain):
                    return name
            return domain or "Live Web"
        except Exception:
            return "Live Web"

    def _search_duckduckgo(self, query: str, top_k: int) -> List[WebSearchResult]:
        """Thực hiện tìm kiếm qua ddgs."""
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS  # type: ignore
            except ImportError:
                logger.warning("Thư viện 'ddgs' hoặc 'duckduckgo-search' chưa được cài đặt.")
                return []

        results: List[WebSearchResult] = []
        try:
            ddgs_client = DDGS(timeout=int(self.timeout_sec))
            # Tra cứu văn bản pháp luật
            raw_results = list(ddgs_client.text(query, max_results=top_k * 2))
            
            for item in raw_results:
                title = item.get("title", "").strip()
                url = item.get("href", "").strip()
                snippet = item.get("body", "").strip()
                if not title or not url:
                    continue

                source_name = self._get_source_name(url)
                
                # Tính điểm ưu tiên cho nguồn pháp luật chính thống
                is_trusted = any(td in url.lower() for td in TRUSTED_LEGAL_DOMAINS)
                score = 1.0 if is_trusted else 0.8

                results.append(
                    WebSearchResult(
                        title=title,
                        snippet=snippet,
                        url=url,
                        source_name=source_name,
                        score=score,
                    )
                )
                if len(results) >= top_k:
                    break
        except Exception as e:
            logger.warning(f"Lỗi khi gọi DuckDuckGo live search: {e}")
            return []

        return results

    def _search_serper(self, query: str, top_k: int) -> List[WebSearchResult]:
        """Tìm kiếm qua Google Serper API nếu có SERPER_API_KEY."""
        api_key = os.environ.get("SERPER_API_KEY")
        if not api_key:
            return []

        url = "https://google.serper.dev/search"
        payload = json.dumps({"q": query, "num": top_k, "gl": "vn", "hl": "vi"}).encode("utf-8")
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            
            results = []
            organic = data.get("organic", [])
            for item in organic[:top_k]:
                link = item.get("link", "")
                results.append(
                    WebSearchResult(
                        title=item.get("title", ""),
                        snippet=item.get("snippet", ""),
                        url=link,
                        source_name=self._get_source_name(link),
                        score=1.0,
                    )
                )
            return results
        except Exception as e:
            logger.warning(f"Lỗi khi gọi Serper API: {e}")
            return []

    def _search_tavily(self, query: str, top_k: int) -> List[WebSearchResult]:
        """Tìm kiếm qua Tavily API nếu có TAVILY_API_KEY."""
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return []

        url = "https://api.tavily.com/search"
        payload = json.dumps({
            "api_key": api_key,
            "query": query,
            "max_results": top_k,
            "search_depth": "basic",
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = []
            for item in data.get("results", [])[:top_k]:
                link = item.get("url", "")
                results.append(
                    WebSearchResult(
                        title=item.get("title", ""),
                        snippet=item.get("content", ""),
                        url=link,
                        source_name=self._get_source_name(link),
                        score=item.get("score", 1.0),
                    )
                )
            return results
        except Exception as e:
            logger.warning(f"Lỗi khi gọi Tavily API: {e}")
            return []

    def search(
        self, query: str, transformed_query: str = "", top_k: int = 3
    ) -> SearchResponse:
        """
        Thực hiện tìm kiếm live web thực tế.
        Sử dụng transformed_query nếu có, ngược lại dùng query gốc.
        """
        search_query = transformed_query.strip() or query.strip()
        start_time = time.time()
        results: List[WebSearchResult] = []

        # 1. Thử Serper nếu có API key
        if os.environ.get("SERPER_API_KEY"):
            results = self._search_serper(search_query, top_k)
            provider_used = "serper"

        # 2. Thử Tavily nếu có API key
        if not results and os.environ.get("TAVILY_API_KEY"):
            results = self._search_tavily(search_query, top_k)
            provider_used = "tavily"

        # 3. Mặc định dùng DuckDuckGo (ddgs)
        if not results:
            results = self._search_duckduckgo(search_query, top_k)
            provider_used = "duckduckgo"

        latency = time.time() - start_time
        return SearchResponse(
            query=query,
            transformed_query=transformed_query,
            results=results,
            latency=latency,
            provider=provider_used,
            total_found=len(results),
        )
