from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable


@dataclass(frozen=True)
class AlpacaNewsItem:
    news_id: str
    headline: str
    source: str
    url: str | None
    summary: str
    created_at: datetime | None
    updated_at: datetime | None
    symbols: tuple[str, ...]
    content: str
    author: str | None = None


class AlpacaNewsAdapter:
    """Read-only Alpaca market-news boundary for the CATS operating loop."""

    def __init__(self, api_key: str, api_secret: str, news_client: Any | None = None):
        if news_client is None:
            from alpaca.data.historical.news import NewsClient

            news_client = NewsClient(api_key, api_secret)
        self.client = news_client

    def get_news(
        self,
        symbols: Iterable[str],
        *,
        start: datetime | None = None,
        limit: int = 50,
    ) -> list[AlpacaNewsItem]:
        clean_symbols = tuple(
            sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()})
        )
        if not clean_symbols:
            return []

        from alpaca.data.requests import NewsRequest

        request = NewsRequest(
            symbols=",".join(clean_symbols),
            start=start,
            sort="desc",
            limit=int(limit),
            include_content=True,
        )
        response = self.client.get_news(request)
        data = getattr(response, "data", None)
        if isinstance(data, dict):
            articles = data.get("news", [])
        elif isinstance(response, dict):
            articles = response.get("news", [])
        else:
            articles = []

        items: list[AlpacaNewsItem] = []
        for article in articles:
            if isinstance(article, dict):
                value = article.get
            else:
                value = lambda key, default=None, article=article: getattr(article, key, default)
            items.append(
                AlpacaNewsItem(
                    news_id=str(value("id", "")),
                    headline=str(value("headline", "") or ""),
                    source=str(value("source", "") or ""),
                    url=(None if value("url") is None else str(value("url"))),
                    summary=str(value("summary", "") or ""),
                    created_at=value("created_at"),
                    updated_at=value("updated_at"),
                    symbols=tuple(str(s).upper() for s in (value("symbols", []) or [])),
                    content=str(value("content", "") or ""),
                    author=(None if value("author") is None else str(value("author"))),
                )
            )
        return items
