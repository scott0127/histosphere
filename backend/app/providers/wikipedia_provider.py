"""Wikipedia source provider.

本模組負責抓取 zh/en Wikipedia 事件資料，並統一轉成 WikiSource。
V1 支援 summary 與 full 兩種 fetch_mode；full 會盡量取得完整條目 extract，
summary 則使用 REST summary endpoint 作為較輕量的 fallback。

抓取策略:
    1. 依序嘗試中文（zh）與英文（en）Wikipedia。
    2. 兩者皆失敗時建立 fallback WikiSource 標記待補。
    3. 中文內容會經過 ``normalize_display_text`` 轉換。
"""

from typing import Any, Literal
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.models.domain import WikiSource
from app.utils.text_normalizer import normalize_display_text


FetchMode = Literal["summary", "full"]
"""Wikipedia 擷取模式：``"summary"``（REST 輕量）或 ``"full"``（MediaWiki 完整）。"""


class WikipediaProvider:
    """從 Wikipedia API 抓取歷史事件來源資料。

    支援 zh/en 雙語擷取，並保留完整 raw payload 供除錯。
    中文內容會自動經過繁體正規化處理。

    Attributes:
        settings: 全域設定實例（提供 timeout 與 User-Agent）。
        headers: HTTP 請求標頭（含 User-Agent）。
    """

    def __init__(self, settings: Settings) -> None:
        """初始化 Wikipedia provider。

        Args:
            settings: 全域 Settings 實例，提供
                ``wikipedia_timeout_seconds`` 與 ``wikipedia_user_agent``。
        """
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
        """依序抓取中文與英文來源；兩者都失敗時建立 fallback source。

        先嘗試 zh 再嘗試 en，只要任一語言成功即回傳。
        若全部失敗，建立一筆 ``fetch_status="fallback"`` 的
        WikiSource 標記此事件的 Wikipedia 資料待補。

        Args:
            event_id: 關聯事件的 UUID 字串。
            event_name: 事件名稱，用於 Wikipedia 查詢。
            fetch_mode: 擷取模式，預設 ``"summary"``。

        Returns:
            list[WikiSource]: 至少一筆 WikiSource（可能為 fallback）。
        """
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
        """依 fetch_mode 決定先抓完整條目或直接抓摘要。

        若 ``fetch_mode="full"``，先嘗試完整條目 API，失敗時
        自動 fallback 到 summary API。

        Args:
            event_id: 關聯事件的 UUID 字串。
            event_name: 事件名稱。
            language: 目標語言代碼（``"zh"`` / ``"en"``）。
            fetch_mode: 擷取模式。

        Returns:
            WikiSource | None: 成功擷取的來源，或 None。
        """
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
        """使用 REST summary API 抓取短摘要。

        適合快速建立事件脈絡，回傳較精簡的 extract。
        404 或 HTTP error 時回傳 None。

        Args:
            event_id: 關聯事件的 UUID 字串。
            event_name: 事件名稱。
            language: 目標語言代碼。

        Returns:
            WikiSource | None: 成功擷取的來源，或 None。
        """
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
        """使用 MediaWiki API 抓取完整純文字 extract。

        供 LLM 產生較完整事件資料時使用。使用
        ``action=query`` + ``prop=extracts|info`` 取得完整文字。
        頁面不存在或 HTTP error 時回傳 None。

        Args:
            event_id: 關聯事件的 UUID 字串。
            event_name: 事件名稱。
            language: 目標語言代碼。

        Returns:
            WikiSource | None: 成功擷取的來源，或 None。
        """
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
