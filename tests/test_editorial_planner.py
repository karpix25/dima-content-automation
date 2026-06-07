from types import SimpleNamespace

from content_automation.editorial_planner import plan_editorial_briefs


def test_planner_returns_count_for_empty_history():
    briefs = plan_editorial_briefs([], count=3)

    assert len(briefs) == 3
    assert [brief.content_format for brief in briefs] == ["money_leak", "teardown", "myth_vs_reality"]
    assert all(brief.series_name for brief in briefs)


def test_planner_avoids_recently_overused_format():
    existing = [
        SimpleNamespace(raw={"content_format": "money_leak", "content_pillar": "profit_economics"}),
        SimpleNamespace(raw={"content_format": "money_leak", "content_pillar": "profit_economics"}),
        SimpleNamespace(raw={"content_format": "teardown", "content_pillar": "acquisition"}),
    ]

    briefs = plan_editorial_briefs(existing, count=2)

    assert "money_leak" not in [brief.content_format for brief in briefs]
    assert briefs[0].content_pillar not in {"profit_economics", "acquisition"}


def test_planner_counts_pending_payloads_inside_current_refill():
    briefs = plan_editorial_briefs(
        [],
        count=1,
        pending_payloads=[{"content_format": "money_leak", "content_pillar": "profit_economics"}],
    )

    assert briefs[0].content_format == "teardown"
    assert briefs[0].content_pillar != "profit_economics"
