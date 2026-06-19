import json
from types import SimpleNamespace

import pytest

from content_automation.idea_bank import IdeaBank
from content_automation.notebooklm_content_plan import (
    build_producer_plan_prompt,
    format_existing_plan_context,
    generate_notebooklm_content_plan,
    normalize_producer_plan,
)
from content_automation.notebooklm_ideas import (
    build_notebooklm_ideas_prompt,
    generate_notebooklm_ideas,
    normalize_notebooklm_ideas,
)


def test_notebooklm_ideas_prompt_can_force_russian():
    prompt = build_notebooklm_ideas_prompt(count=5, content_language="ru")

    assert "5 strong Russian content topic ideas" in prompt
    assert "natural Russian" in prompt
    assert "Viral angle requirements" in prompt
    assert '"hook_pattern": ""' in prompt
    assert '"mechanism": ""' in prompt
    assert '"first_frame_text": ""' in prompt


def test_normalize_notebooklm_ideas_marks_source():
    ideas = normalize_notebooklm_ideas(
        {
            "ideas": [
                {
                    "title": "Margin leak",
                    "pain": "Fees",
                    "angle": "Audit FBA tiers",
                    "viral_angle": "villain",
                    "hook_pattern": "negative urgency",
                    "mechanism": "fee tier mismatch",
                    "first_frame_text": "FEE LEAK",
                    "visual_proof": "FBA fee table",
                    "summary": "Source note",
                }
            ]
        },
        notebook_ref="notebook-1",
    )

    assert ideas[0]["source"] == "notebooklm"
    assert ideas[0]["source_url"].startswith("notebooklm://notebook-1/")
    assert ideas[0]["source_meta"]["notebook_ref"] == "notebook-1"
    assert ideas[0]["source_meta"]["hook_pattern"] == "negative urgency"
    assert ideas[0]["source_meta"]["mechanism"] == "fee tier mismatch"
    assert ideas[0]["source_meta"]["first_frame_text"] == "FEE LEAK"
    assert ideas[0]["source_meta"]["visual_proof"] == "FBA fee table"


@pytest.mark.asyncio
async def test_generate_notebooklm_ideas_saves_to_idea_bank(tmp_path):
    class FakeNotebookLM:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            assert "content topic ideas" in question
            assert notebook_url.endswith("/notebook-1")
            return SimpleNamespace(
                answer='[{"title":"Buy Box risk","pain":"Margin drops","angle":"Audit offer health","summary":"Notebook note"}]'
            )

    bank = IdeaBank(tmp_path / "ideas.sqlite3")

    inserted = await generate_notebooklm_ideas(
        user_id="42",
        notebook_ref="notebook-1",
        notebooklm=FakeNotebookLM(),
        idea_bank=bank,
        count=3,
        content_language="en",
    )

    assert len(inserted) == 1
    assert inserted[0].source == "notebooklm"
    assert bank.list_new("42")[0].title == "Buy Box risk"


def test_producer_plan_prompt_uses_social_producer_role_and_language():
    prompt = build_producer_plan_prompt(count=30, content_language="ru", offer_context="Amazon mentorship")

    assert "senior social media producer" in prompt
    assert "Create 30 fresh content episode(s)" in prompt
    assert "natural Russian" in prompt
    assert "Amazon mentorship" in prompt
    assert "Viral angle requirements" in prompt
    assert "viral_angle, hook_pattern, mechanism, first_frame_text" in prompt


def test_producer_plan_extension_prompt_includes_saved_topics():
    existing = [
        _idea_for_plan(title="Fee Leak", angle="Audit FBA tiers", day=1),
        _idea_for_plan(title="ACOS Trap", angle="Separate ranking from profit", day=2),
    ]

    prompt = build_producer_plan_prompt(
        count=30,
        content_language="en",
        offer_context="Amazon mentorship",
        existing_ideas=existing,
        extension=True,
    )

    assert "Do not restart the plan" in prompt
    assert "Fee Leak | Audit FBA tiers" in prompt
    assert "ACOS Trap | Separate ranking from profit" in prompt


def test_format_existing_plan_context_has_empty_fallback():
    assert format_existing_plan_context([]) == "- No saved topics yet."


def test_normalize_producer_plan_marks_metadata():
    ideas = normalize_producer_plan(
        {
            "plan": [
                {
                    "day": 3,
                    "pillar": "Margin",
                    "format": "vertical_short",
                    "title": "Fee Leak",
                    "pain": "Profit disappears",
                    "angle": "Audit FBA tiers",
                    "viral_angle": "villain",
                    "hook_pattern": "specificity slam",
                    "mechanism": "box size changes the fee tier",
                    "first_frame_text": "CHECK THIS FEE",
                    "summary": "Catch box-size mistakes.",
                    "visual_note": "Show carton and fee table",
                    "visual_proof": "Before/after fee table",
                    "source_basis": "Notebook note",
                }
            ]
        },
        notebook_ref="notebook-1",
    )

    assert ideas[0]["source"] == "notebooklm_plan"
    assert ideas[0]["source_meta"]["day"] == 3
    assert ideas[0]["source_meta"]["pillar"] == "Margin"
    assert ideas[0]["source_meta"]["visual_note"] == "Show carton and fee table"
    assert ideas[0]["source_meta"]["viral_angle"] == "villain"
    assert ideas[0]["source_meta"]["hook_pattern"] == "specificity slam"
    assert ideas[0]["source_meta"]["mechanism"] == "box size changes the fee tier"
    assert ideas[0]["source_meta"]["first_frame_text"] == "CHECK THIS FEE"
    assert ideas[0]["source_meta"]["visual_proof"] == "Before/after fee table"


@pytest.mark.asyncio
async def test_generate_notebooklm_content_plan_saves_to_idea_bank(tmp_path):
    class FakeNotebookLM:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            assert "fresh content episode" in question
            assert notebook_url.endswith("/notebook-1")
            return SimpleNamespace(
                answer='{"plan":[{"day":1,"pillar":"PPC","format":"vertical_short","title":"ACOS Trap","pain":"Ad waste","angle":"Separate ranking from profit","summary":"Notebook note","visual_note":"PPC dashboard","source_basis":"Source"}]}'
            )

    bank = IdeaBank(tmp_path / "ideas.sqlite3")

    inserted = await generate_notebooklm_content_plan(
        user_id="42",
        notebook_ref="notebook-1",
        notebooklm=FakeNotebookLM(),
        idea_bank=bank,
        count=30,
        content_language="en",
    )

    assert len(inserted) == 1
    assert inserted[0].source == "notebooklm_plan"
    assert bank.list_new("42")[0].title == "ACOS Trap"


@pytest.mark.asyncio
async def test_generate_notebooklm_content_plan_splits_large_plan_into_batches(tmp_path):
    class FakeNotebookLM:
        def __init__(self):
            self.questions = []
            self.topic_words = [
                ("Fees", "tier audit", "fee table"),
                ("Inventory", "stockout forecast", "inventory calendar"),
                ("PPC", "keyword pruning", "ads dashboard"),
                ("Reviews", "trust repair", "review timeline"),
                ("BuyBox", "offer health", "buy box panel"),
                ("Logistics", "shipping delay", "freight map"),
                ("Cashflow", "payout gap", "cash bridge"),
                ("Listing", "image hierarchy", "listing mockup"),
                ("Returns", "refund leak", "return report"),
                ("Supplier", "moq negotiation", "factory quote"),
                ("Compliance", "document check", "approval notice"),
                ("Catalog", "variation cleanup", "catalog tree"),
                ("Launch", "ranking sprint", "launch board"),
                ("Forecast", "demand curve", "sales chart"),
                ("Pricing", "elasticity test", "price matrix"),
                ("Brand", "positioning gap", "brand shelf"),
                ("Warehouse", "storage fee", "warehouse bins"),
                ("Creative", "hook testing", "creative wall"),
                ("Coupons", "discount trap", "coupon badge"),
                ("Analytics", "metric blindspot", "analytics screen"),
                ("Bundles", "kit margin", "bundle layout"),
                ("Search", "query intent", "search results"),
                ("Packaging", "box dimension", "packaging ruler"),
                ("Team", "delegation map", "org chart"),
                ("Exit", "valuation driver", "deal room"),
                ("Defects", "quality control", "inspection sheet"),
                ("Seasonality", "holiday demand", "season calendar"),
                ("Keywords", "semantic cluster", "keyword map"),
                ("Quality", "defect prevention", "qa checklist"),
                ("Expansion", "market filter", "country scorecard"),
            ]

        def ask(self, question, *, notebook_url=None, notebook_id=None):
            self.questions.append(question)
            call = len(self.questions)
            word, angle, visual = self.topic_words[call - 1]
            items = [
                {
                    "day": call,
                    "pillar": "Operations",
                    "format": "vertical_short",
                    "title": f"{word} system",
                    "pain": f"Problem around {angle}",
                    "angle": f"Show {angle}",
                    "summary": f"Teach {word.lower()} with a concrete operator example.",
                    "visual_note": visual,
                    "source_basis": f"{word} source note",
                }
            ]
            return SimpleNamespace(answer=json.dumps({"plan": items}))

    notebooklm = FakeNotebookLM()
    bank = IdeaBank(tmp_path / "ideas.sqlite3")

    inserted = await generate_notebooklm_content_plan(
        user_id="42",
        notebook_ref="notebook-1",
        notebooklm=notebooklm,
        idea_bank=bank,
        count=25,
        content_language="en",
    )

    assert len(inserted) == 25
    assert len(notebooklm.questions) == 25
    assert "Create 1 fresh content episode(s)" in notebooklm.questions[0]
    assert "Fees system | Show tier audit" in notebooklm.questions[1]
    assert "Analytics system | Show metric blindspot" in notebooklm.questions[20]


@pytest.mark.asyncio
async def test_generate_notebooklm_content_plan_retries_after_duplicate_batch(tmp_path):
    class FakeNotebookLM:
        def __init__(self):
            self.questions = []
            self.items = [
                ("Fees", "tier audit", "fee table"),
                ("Fees", "tier audit", "fee table"),
                ("Inventory", "stockout forecast", "inventory calendar"),
                ("PPC", "keyword pruning", "ads dashboard"),
            ]

        def ask(self, question, *, notebook_url=None, notebook_id=None):
            self.questions.append(question)
            call = len(self.questions)
            word, angle, visual = self.items[call - 1]
            item = {
                "day": 1 if call == 2 else call,
                "pillar": "Operations",
                "format": "vertical_short",
                "title": f"{word} system",
                "pain": f"Problem around {angle}",
                "angle": f"Show {angle}",
                "summary": f"Teach {word.lower()} with a concrete operator example.",
                "visual_note": visual,
                "source_basis": f"{word} source note",
            }
            return SimpleNamespace(answer=json.dumps({"plan": [item]}))

    notebooklm = FakeNotebookLM()
    bank = IdeaBank(tmp_path / "ideas.sqlite3")

    inserted = await generate_notebooklm_content_plan(
        user_id="42",
        notebook_ref="notebook-1",
        notebooklm=notebooklm,
        idea_bank=bank,
        count=3,
        content_language="en",
    )

    assert len(inserted) == 3
    assert len(notebooklm.questions) == 4
    assert [idea.title for idea in inserted] == ["Fees system", "Inventory system", "PPC system"]


def _idea_for_plan(*, title: str, angle: str, day: int):
    from content_automation.idea_bank import ContentIdea

    return ContentIdea(
        id=day,
        user_id="42",
        source="notebooklm_plan",
        source_url=f"notebooklm://notebook-1/plan-day-{day}",
        status="new",
        title=title,
        pain="Pain",
        angle=angle,
        summary="Summary",
        source_meta={"day": day, "pillar": "Margin"},
        fingerprint=title.lower(),
        created_at="",
        updated_at="",
    )
