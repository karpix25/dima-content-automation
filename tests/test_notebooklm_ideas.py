from types import SimpleNamespace

import pytest

from content_automation.idea_bank import IdeaBank
from content_automation.notebooklm_ideas import (
    build_notebooklm_ideas_prompt,
    generate_notebooklm_ideas,
    normalize_notebooklm_ideas,
)


def test_notebooklm_ideas_prompt_can_force_russian():
    prompt = build_notebooklm_ideas_prompt(count=5, content_language="ru")

    assert "5 strong Russian content topic ideas" in prompt
    assert "natural Russian" in prompt


def test_normalize_notebooklm_ideas_marks_source():
    ideas = normalize_notebooklm_ideas(
        {"ideas": [{"title": "Margin leak", "pain": "Fees", "angle": "Audit FBA tiers", "summary": "Source note"}]},
        notebook_ref="notebook-1",
    )

    assert ideas[0]["source"] == "notebooklm"
    assert ideas[0]["source_url"].startswith("notebooklm://notebook-1/")
    assert ideas[0]["source_meta"]["notebook_ref"] == "notebook-1"


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
