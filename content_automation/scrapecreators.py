from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class ScrapeCreatorsError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScrapeCreatorsClient:
    api_key: str | None
    base_url: str = "https://api.scrapecreators.com"
    timeout_seconds: float = 45

    def reddit_subreddit_search(
        self,
        *,
        subreddit: str,
        query: str,
        sort: str = "new",
        timeframe: str = "week",
    ) -> dict[str, Any]:
        return self._get(
            "/v1/reddit/subreddit/search",
            {
                "subreddit": subreddit.removeprefix("r/"),
                "query": query,
                "sort": sort,
                "timeframe": timeframe,
            },
        )

    def instagram_reels_search(self, *, query: str, date_posted: str = "last-week", page: int = 1) -> dict[str, Any]:
        return self._get(
            "/v2/instagram/reels/search",
            {
                "query": query,
                "date_posted": date_posted,
                "page": page,
            },
        )

    def instagram_trending_reels(self) -> dict[str, Any]:
        return self._get("/v1/instagram/reels/trending", {})

    def instagram_comments(self, *, url: str, cursor: str | None = None) -> dict[str, Any]:
        params = {"url": url}
        if cursor:
            params["cursor"] = cursor
        return self._get("/v2/instagram/post/comments", params)

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise ScrapeCreatorsError("SCRAPECREATORS_API_KEY не задан в .env")
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = httpx.get(url, headers={"x-api-key": self.api_key}, params=params, timeout=self.timeout_seconds)
        except httpx.HTTPError as exc:
            raise ScrapeCreatorsError(f"ScrapeCreators request failed: {exc}") from exc
        if response.status_code >= 400:
            raise ScrapeCreatorsError(f"ScrapeCreators HTTP {response.status_code}: {response.text[:1000]}")
        try:
            data = response.json()
        except ValueError as exc:
            raise ScrapeCreatorsError(f"ScrapeCreators returned non-JSON response: {response.text[:1000]}") from exc
        return data if isinstance(data, dict) else {"response": data}
