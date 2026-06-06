from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .scrapecreators import ScrapeCreatorsClient


DEFAULT_REDDIT_QUERIES = (
    "Amazon FBA fees",
    "Amazon PPC",
    "Amazon ranking",
    "Amazon returns",
    "Amazon inventory",
    "Seller Central",
    "Buy Box",
    "FBA launch",
)


@dataclass(frozen=True)
class RedditRadarPost:
    subreddit: str
    title: str
    url: str
    score: int
    comments: int
    query: str


def collect_reddit_ideas(
    client: ScrapeCreatorsClient,
    *,
    subreddits: tuple[str, ...],
    queries: tuple[str, ...] = DEFAULT_REDDIT_QUERIES,
    timeframe: str = "week",
    limit: int = 10,
) -> list[dict[str, Any]]:
    posts = collect_reddit_posts(client, subreddits=subreddits, queries=queries, timeframe=timeframe)
    posts.sort(key=lambda post: (post.comments, post.score), reverse=True)
    return [_post_to_idea(post) for post in posts[:limit]]


def collect_reddit_posts(
    client: ScrapeCreatorsClient,
    *,
    subreddits: tuple[str, ...],
    queries: tuple[str, ...] = DEFAULT_REDDIT_QUERIES,
    timeframe: str = "week",
) -> list[RedditRadarPost]:
    posts: list[RedditRadarPost] = []
    seen: set[str] = set()
    for subreddit in subreddits:
        for query in queries:
            payload = client.reddit_subreddit_search(subreddit=subreddit, query=query, sort="comments", timeframe=timeframe)
            for post in _extract_posts(payload, subreddit=subreddit, query=query):
                key = post.url or post.title.lower()
                if key in seen:
                    continue
                seen.add(key)
                posts.append(post)
    return posts


def _extract_posts(payload: dict[str, Any], *, subreddit: str, query: str) -> list[RedditRadarPost]:
    raw_posts = payload.get("posts") if isinstance(payload.get("posts"), list) else []
    posts: list[RedditRadarPost] = []
    for raw in raw_posts:
        if not isinstance(raw, dict):
            continue
        title = _clean_text(raw.get("title") or raw.get("text") or raw.get("body"), max_length=220)
        if not title or _looks_low_signal(title):
            continue
        url = _reddit_url(raw.get("url") or raw.get("permalink"))
        comments = _to_int(raw.get("num_comments") or raw.get("comment_count"))
        score = _to_int(raw.get("score") or raw.get("upvote_count"))
        posts.append(
            RedditRadarPost(
                subreddit=subreddit,
                title=title,
                url=url,
                score=score,
                comments=comments,
                query=query,
            )
        )
    return posts


def _post_to_idea(post: RedditRadarPost) -> dict[str, Any]:
    pain = infer_pain(post.title)
    return {
        "source": "reddit",
        "source_url": post.url,
        "title": post.title,
        "pain": pain,
        "angle": infer_angle(post.title, pain),
        "summary": f"Discussion in r/{post.subreddit}: {post.comments} comments, {post.score} upvotes.",
        "source_meta": {
            "subreddit": post.subreddit,
            "query": post.query,
            "score": post.score,
            "comments": post.comments,
        },
    }


def infer_pain(title: str) -> str:
    lowered = title.lower()
    if any(term in lowered for term in ("fee", "fees", "profit", "margin", "ppc")):
        return "Sellers may see sales growth while Amazon fees, ads, or hidden costs eat the actual profit."
    if any(term in lowered for term in ("rank", "ranking", "launch", "keyword")):
        return "Sellers are unsure which launch and ranking actions still move the needle."
    if any(term in lowered for term in ("return", "returned", "refund")):
        return "Returns and return-related badges can damage conversion, margin, and buyer trust."
    if any(term in lowered for term in ("inventory", "logistics", "awd", "global logistics", "stock")):
        return "Inventory and logistics choices are directly affecting cash flow and operational control."
    if any(term in lowered for term in ("letter", "policy", "section 3", "flagged", "suppressed")):
        return "Compliance, policy, and brand enforcement can stop sales before ads have time to pay back."
    return "Sellers are looking for a practical answer to a current Amazon business problem."


def infer_angle(title: str, pain: str) -> str:
    if "profit" in title.lower() or "margin" in title.lower():
        return "Show why revenue without unit economics creates a false sense of growth."
    if "ranking" in title.lower():
        return "Explain why old ranking tactics stop working and what operators should check first."
    if "returns" in title.lower() or "returned" in title.lower():
        return "Explain how one return reason can become a system-wide conversion leak."
    if "flagged" in title.lower() or "suppressed" in title.lower():
        return "Show how to prepare the listing and supply chain before Amazon hits stop."
    return pain


def _clean_text(value: object, *, max_length: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "..."


def _looks_low_signal(title: str) -> bool:
    lowered = title.strip().lower()
    return lowered in {"help", "question", "need advice"} or len(lowered) < 12


def _reddit_url(value: object) -> str:
    url = str(value or "").strip()
    if url.startswith("/"):
        return f"https://www.reddit.com{url}"
    return url


def _to_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
