from typing import Any, Literal

import httpx

from app.core.config import Settings
from app.models.domain import WikiSource


FetchMode = Literal["summary", "full"]


class WikipediaProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_sources(
        self,
        event_id: str,
        event_name: str,
        fetch_mode: FetchMode = "summary",
    ) -> list[WikiSource]:
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
        url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{event_name}"
        try:
            async with httpx.AsyncClient(timeout=self.settings.wikipedia_timeout_seconds) as client:
                response = await client.get(url, headers={"accept": "application/json"})
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
        return WikiSource(
            event_id=event_id,
            language=language,
            title=payload.get("title") or event_name,
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
                response = await client.get(url, headers={"accept": "application/json"}, params=params)
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

        return WikiSource(
            event_id=event_id,
            language=language,
            title=page.get("title") or event_name,
            page_url=page.get("fullurl"),
            summary=summary,
            provider="wikipedia",
            fetch_mode="full",
            fetch_status="success",
            raw_payload=payload,
        )
