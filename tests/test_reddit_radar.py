from pathlib import Path

from content_automation.config import normalize_scrapecreators_timeframe
from content_automation.idea_bank import ContentIdea, IdeaBank
from content_automation.idea_cards import idea_to_topic_hint, select_visible_idea
from content_automation.reddit_radar import collect_reddit_ideas


class FakeRedditClient:
    def __init__(self):
        self.calls = []

    def reddit_subreddit_search(self, *, subreddit, query, sort="comments", timeframe="week"):
        self.calls.append({"subreddit": subreddit, "query": query, "sort": sort, "timeframe": timeframe})
        return {
            "posts": [
                {
                    "title": f"{query}: Amazon fees and PPC make profit impossible",
                    "permalink": f"/r/{subreddit}/comments/1/example",
                    "score": 12,
                    "num_comments": 40,
                },
                {
                    "title": "Help",
                    "permalink": f"/r/{subreddit}/comments/2/low_signal",
                    "score": 1,
                    "num_comments": 99,
                },
            ]
        }


def test_collect_reddit_ideas_filters_and_builds_angles():
    client = FakeRedditClient()
    ideas = collect_reddit_ideas(
        client,
        subreddits=("AmazonFBA",),
        queries=("Amazon FBA fees",),
        timeframe="day",
        limit=10,
    )

    assert len(ideas) == 1
    assert client.calls[0]["timeframe"] == "day"
    assert ideas[0]["source"] == "reddit"
    assert "прибыль" in ideas[0]["pain"]
    assert ideas[0]["source_url"] == "https://www.reddit.com/r/AmazonFBA/comments/1/example"


def test_idea_bank_deduplicates_similar_topics(tmp_path: Path):
    bank = IdeaBank(tmp_path / "ideas.sqlite3")
    idea = {
        "source": "reddit",
        "source_url": "https://reddit.test/1",
        "title": "Amazon fees and PPC make profit impossible",
        "pain": "Sellers lose margin to ads and fees.",
        "angle": "Revenue without unit economics is fake growth.",
        "summary": "40 comments",
        "source_meta": {"comments": 40},
    }

    first = bank.add_if_new("42", idea)
    second = bank.add_if_new("42", {**idea, "source_url": "https://reddit.test/2"})

    assert first is not None
    assert second is None
    assert len(bank.list_new("42")) == 1


def test_idea_to_topic_hint_keeps_source_context(tmp_path: Path):
    bank = IdeaBank(tmp_path / "ideas.sqlite3")
    idea = bank.add_if_new(
        "42",
        {
            "source": "reddit",
            "source_url": "https://reddit.test/1",
            "title": "Amazon returns badge hurt conversion",
            "pain": "Returns destroy trust.",
            "angle": "Explain the hidden conversion cost of returns.",
            "summary": "11 comments",
        },
    )

    hint = idea_to_topic_hint(idea)

    assert "Reddit title: Amazon returns badge hurt conversion" in hint
    assert "Do not quote Reddit directly" in hint


def test_select_visible_idea_moves_to_next_card(tmp_path: Path):
    first = make_idea(1, "First Amazon PPC topic")
    second = make_idea(2, "Inventory storage limit crisis")
    ideas = [second, first]

    assert [idea.id for idea in ideas] == [second.id, first.id]
    assert select_visible_idea(ideas, after_id=second.id).id == first.id
    assert select_visible_idea(ideas, after_id=first.id).id == second.id


def test_normalize_scrapecreators_timeframe():
    assert normalize_scrapecreators_timeframe("day") == "day"
    assert normalize_scrapecreators_timeframe("bad") == "week"


def idea_payload(url: str, title: str) -> dict[str, object]:
    return {
        "source": "reddit",
        "source_url": url,
        "title": title,
        "pain": f"Sellers need a practical answer about {title}.",
        "angle": f"Turn {title} into a clear operating lesson.",
        "summary": "10 comments",
    }


def make_idea(idea_id: int, title: str) -> ContentIdea:
    return ContentIdea(
        id=idea_id,
        user_id="42",
        source="reddit",
        source_url=f"https://reddit.test/{idea_id}",
        status="new",
        title=title,
        pain=f"Pain {idea_id}",
        angle=f"Angle {idea_id}",
        summary="10 comments",
        source_meta={},
        fingerprint=title.lower(),
        created_at="",
        updated_at="",
    )
