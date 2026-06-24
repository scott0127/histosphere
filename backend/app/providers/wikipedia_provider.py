"""Wikipedia source provider.

本模組負責抓取 zh/en Wikipedia 事件資料，並統一轉成 WikiSource。
V1 支援 summary 與 full 兩種 fetch_mode；full 會盡量取得完整條目 extract，
summary 則使用 REST summary endpoint 作為較輕量的 fallback。
"""

from typing import Any, Literal
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.models.domain import WikiSource
from app.utils.text_normalizer import normalize_display_text


FetchMode = Literal["summary", "full"]


class WikipediaProvider:
    """抓取 Wikipedia 來源資料並保留可追溯 metadata。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.headers = {
            "accept": "application/json",
            # Wikimedia 會拒絕缺少 User-Agent 的 API 請求；此值可用 WIKIPEDIA_USER_AGENT 覆蓋。
            "user-agent": settings.wikipedia_user_agent,
        }

    async def fetch_sources(
        self,
        event_id: str,
        event_name: str,
        fetch_mode: FetchMode = "summary",
    ) -> list[WikiSource]:
        """依序抓取中文與英文來源；兩者都失敗時建立 fallback source。"""
        sources: list[WikiSource] = []
        for language in ("zh", "en"):
            source = await self._fetch_source(event_id, event_name, language, fetch_mode)
            if source:
                sources.append(source)
        if sources:
            return sources
        return [
            WikiSource(
                event_id=event_id,
                language="zh",
                title=event_name,
                page_url=None,
                summary=f"{event_name} 的 Wikipedia 資料暫時無法取得。此資料列為待補來源。",
                provider="wikipedia",
                fetch_mode=fetch_mode,
                fetch_status="fallback",
                raw_payload={"provider_status": "fallback"},
            )
        ]

    async def _fetch_source(
        self,
        event_id: str,
        event_name: str,
        language: Literal["zh", "en"],
        fetch_mode: FetchMode,
    ) -> WikiSource | None:
        """依 fetch_mode 決定先抓完整條目或直接抓摘要。"""
        if fetch_mode == "full":
            source = await self._fetch_full(event_id, event_name, language)
            if source:
                return source
        return await self._fetch_summary(event_id, event_name, language)

    async def _fetch_summary(
        self,
        event_id: str,
        event_name: str,
        language: Literal["zh", "en"],
    ) -> WikiSource | None:
        """使用 REST summary API 抓取短摘要，適合快速建立事件脈絡。"""
        encoded_title = quote(event_name, safe="")
        url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
        try:
            async with httpx.AsyncClient(timeout=self.settings.wikipedia_timeout_seconds) as client:
                response = await client.get(url, headers=self.headers)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
        except httpx.HTTPError:
            return None

        payload: dict[str, Any] = response.json()
        summary = payload.get("extract") or ""
        if not summary.strip():
            return None

        page_url = (
            payload.get("content_urls", {})
            .get("desktop", {})
            .get("page")
        )
        title = payload.get("title") or event_name
        if language == "zh":
            title = normalize_display_text(title) or title
            summary = normalize_display_text(summary) or summary
        return WikiSource(
            event_id=event_id,
            language=language,
            title=title,
            page_url=page_url,
            summary=summary,
            provider="wikipedia",
            fetch_mode="summary",
            fetch_status="success",
            raw_payload=payload,
        )

    async def _fetch_full(
        self,
        event_id: str,
        event_name: str,
        language: Literal["zh", "en"],
    ) -> WikiSource | None:
        """使用 MediaWiki API 抓取完整純文字 extract，供 LLM 產生較完整資料。"""
        url = f"https://{language}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "prop": "extracts|info",
            "explaintext": "1",
            "redirects": "1",
            "inprop": "url",
            "titles": event_name,
            "format": "json",
            "formatversion": "2",
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.wikipedia_timeout_seconds) as client:
                response = await client.get(url, headers=self.headers, params=params)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
        except httpx.HTTPError:
            return None

        payload: dict[str, Any] = response.json()
        pages = payload.get("query", {}).get("pages", [])
        page = pages[0] if pages else {}
        if page.get("missing"):
            return None
        summary = page.get("extract") or ""
        if not summary.strip():
            return None
        title = page.get("title") or event_name
        if language == "zh":
            title = normalize_display_text(title) or title
            summary = normalize_display_text(summary) or summary

        return WikiSource(
            event_id=event_id,
            language=language,
            title=title,
            page_url=page.get("fullurl"),
            summary=summary,
            provider="wikipedia",
            fetch_mode="full",
            fetch_status="success",
            raw_payload=payload,
        )
