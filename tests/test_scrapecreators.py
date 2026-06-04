import httpx

from content_automation.scrapecreators import ScrapeCreatorsClient, ScrapeCreatorsError
from content_automation.trend_radar import collect_trend_radar, format_trend_radar


def test_scrapecreators_client_uses_api_key_and_params(monkeypatch):
    calls = []

    def fake_get(url, *, headers, params, timeout):
        calls.append((url, headers, params, timeout))
        return httpx.Response(200, json={"posts": []})

    monkeypatch.setattr(httpx, "get", fake_get)
    client = ScrapeCreatorsClient(api_key="secret", base_url="https://api.example.test", timeout_seconds=12)

    client.reddit_subreddit_search(subreddit="r/FulfillmentByAmazon", query="fees")

    assert calls == [
        (
            "https://api.example.test/v1/reddit/subreddit/search",
            {"x-api-key": "secret"},
            {"subreddit": "FulfillmentByAmazon", "query": "fees", "sort": "new", "timeframe": "week"},
            12,
        )
    ]


def test_scrapecreators_client_requires_key():
    client = ScrapeCreatorsClient(api_key=None)

    try:
        client.instagram_trending_reels()
    except ScrapeCreatorsError as exc:
        assert "SCRAPECREATORS_API_KEY" in str(exc)
    else:
        raise AssertionError("expected ScrapeCreatorsError")


class FakeTrendClient:
    def reddit_subreddit_search(self, *, subreddit, query, sort="new", timeframe="week"):
        return {
            "posts": [
                {
                    "title": f"{query} changed my FBA margin",
                    "permalink": "/r/FulfillmentByAmazon/comments/1/test",
                    "score": 42,
                    "num_comments": 7,
                }
            ]
        }

    def instagram_reels_search(self, *, query, date_posted="last-week", page=1):
        return {
            "reels": [
                {
                    "caption": f"{query} packaging mistake",
                    "url": "https://www.instagram.com/reel/example/",
                    "video_view_count": 1000,
                    "comment_count": 12,
                }
            ]
        }


def test_collect_trend_radar_formats_items():
    result = collect_trend_radar(FakeTrendClient(), query="FBA fees", reddit_subreddits=("FulfillmentByAmazon",), limit=3)
    text = format_trend_radar(result)

    assert "[Reddit r/FulfillmentByAmazon] FBA fees changed my FBA margin" in text
    assert "https://www.reddit.com/r/FulfillmentByAmazon/comments/1/test" in text
    assert "[Instagram Reels] FBA fees packaging mistake" in text
    assert "/daily_scripts фокус: FBA fees" in text
