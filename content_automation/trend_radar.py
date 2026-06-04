from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .scrapecreators import ScrapeCreatorsClient


@dataclass(frozen=True)
class TrendItem:
    source: str
    title: str
    url: str | None = None
    metric: str | None = None


@dataclass(frozen=True)
class TrendRadarResult:
    query: str
    items: tuple[TrendItem, ...]
    errors: tuple[str, ...] = ()


def collect_trend_radar(
    client: ScrapeCreatorsClient,
    *,
    query: str,
    reddit_subreddits: tuple[str, ...],
    limit: int = 5,
) -> TrendRadarResult:
    items: list[TrendItem] = []
    errors: list[str] = []

    for subreddit in reddit_subreddits:
        try:
            payload = client.reddit_subreddit_search(subreddit=subreddit, query=query, sort="new", timeframe="week")
            items.extend(_reddit_items(payload, subreddit, limit))
        except Exception as exc:
            errors.append(f"Reddit r/{subreddit}: {exc}")

    try:
        payload = client.instagram_reels_search(query=query, date_posted="last-week", page=1)
        items.extend(_instagram_reel_items(payload, limit))
    except Exception as exc:
        errors.append(f"Instagram Reels: {exc}")

    return TrendRadarResult(query=query, items=tuple(items[: max(1, limit * 3)]), errors=tuple(errors))


def format_trend_radar(result: TrendRadarResult) -> str:
    if not result.items and result.errors:
        return "Не смог собрать радар тем:\n" + "\n".join(f"- {error}" for error in result.errors[:5])

    lines = [f"Радар тем: {result.query}", ""]
    if result.items:
        for index, item in enumerate(result.items, start=1):
            metric = f" ({item.metric})" if item.metric else ""
            lines.append(f"{index}. [{item.source}] {item.title}{metric}")
            if item.url:
                lines.append(item.url)
    else:
        lines.append("Ничего не нашел по этому запросу.")

    if result.errors:
        lines.extend(["", "Часть источников не ответила:"])
        lines.extend(f"- {error}" for error in result.errors[:3])

    lines.extend(["", "Дальше можно взять один угол и запустить:", f"/daily_scripts фокус: {result.query}"])
    return "\n".join(lines)


def _reddit_items(payload: dict[str, Any], subreddit: str, limit: int) -> list[TrendItem]:
    posts = payload.get("posts") if isinstance(payload.get("posts"), list) else []
    items: list[TrendItem] = []
    for post in posts[:limit]:
        if not isinstance(post, dict):
            continue
        title = _clean_text(post.get("title") or post.get("text") or post.get("body"))
        if not title:
            continue
        score = post.get("score") or post.get("upvote_count")
        comments = post.get("num_comments") or post.get("comment_count")
        metric = _join_metric(score, "up", comments, "comments")
        url = post.get("url") or post.get("permalink")
        items.append(TrendItem(source=f"Reddit r/{subreddit}", title=title, url=_reddit_url(url), metric=metric))
    return items


def _instagram_reel_items(payload: dict[str, Any], limit: int) -> list[TrendItem]:
    reels = payload.get("reels") if isinstance(payload.get("reels"), list) else []
    items: list[TrendItem] = []
    for reel in reels[:limit]:
        if not isinstance(reel, dict):
            continue
        title = _clean_text(reel.get("caption") or reel.get("accessibility_caption") or reel.get("shortcode"))
        if not title:
            continue
        views = reel.get("video_view_count") or reel.get("video_play_count")
        comments = reel.get("comment_count")
        metric = _join_metric(views, "views", comments, "comments")
        items.append(TrendItem(source="Instagram Reels", title=title, url=reel.get("url"), metric=metric))
    return items


def _clean_text(value: object, *, max_length: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "..."


def _join_metric(first: object, first_label: str, second: object, second_label: str) -> str | None:
    parts = []
    if isinstance(first, int | float):
        parts.append(f"{int(first)} {first_label}")
    if isinstance(second, int | float):
        parts.append(f"{int(second)} {second_label}")
    return ", ".join(parts) or None


def _reddit_url(value: object) -> str | None:
    url = str(value or "").strip()
    if not url:
        return None
    if url.startswith("/"):
        return f"https://www.reddit.com{url}"
    return url
