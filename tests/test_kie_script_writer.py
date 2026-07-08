from pathlib import Path
import json

import pytest

from content_automation.idea_bank import ContentIdea
from content_automation.notebooklm_idea_scripts import create_script_from_idea
from content_automation.storage import Storage


def test_create_script_from_idea_uses_kie_without_notebooklm(tmp_path: Path):
    storage = Storage(tmp_path / "scripts.sqlite3")
    notebooklm = FailingNotebookLM()
    kie = FakeKieTextClient(_script_json())

    record = _run(
        create_script_from_idea(
            storage=storage,
            user_id="42",
            idea=_idea(),
            notebook_ref="notebook-1",
            notebooklm=notebooklm,
            author_style="Direct expert",
            offer_context="Amazon profit audit",
            cta_mix="no CTA",
            content_language="en",
            vertical_duration_mode="original",
            script_writer_backend="kie",
            kie_text_client=kie,
        )
    )

    assert record.raw["writer_backend"] == "kie"
    assert record.raw["source_idea_id"] == 7
    assert record.raw["first_frame_text"] == "FEE LEAK"
    assert "NotebookLM factual packet" in kie.calls[0]["user"]


def test_create_script_from_idea_does_not_fallback_to_notebooklm_when_kie_fails(tmp_path: Path):
    storage = Storage(tmp_path / "scripts.sqlite3")
    notebooklm = NotebookLMAnswer(_script_json())

    with pytest.raises(ValueError, match="KIE не смог написать сценарий"):
        _run(
            create_script_from_idea(
                storage=storage,
                user_id="42",
                idea=_idea(),
                notebook_ref="notebook-1",
                notebooklm=notebooklm,
                author_style="Direct expert",
                offer_context="Amazon profit audit",
                cta_mix="no CTA",
                content_language="en",
                vertical_duration_mode="original",
                script_writer_backend="kie",
                kie_text_client=FailingKieTextClient(),
            )
        )

    assert notebooklm.calls == 0


def _run(coro):
    import asyncio

    return asyncio.run(coro)


def _script_json() -> str:
    voiceover = " ".join(["Profit leaks hide inside fee tiers before sellers notice the real margin problem."] * 8)
    return json.dumps(
        [
            {
                "title": "Fee leak",
                "angle": "Audit fee tiers",
                "hook": "Your profit leak is not PPC.",
                "trigger": "FBA tier changed quietly",
                "voiceover": voiceover,
                "cta": "",
                "why_it_works": "Specific operational pain.",
                "source_basis": "Notebook note",
                "first_frame_text": "FEE LEAK",
                "mechanism": "fee tier mismatch",
                "hook_pattern": "specificity slam",
                "visual_proof": "fee table",
                "visual_retention_plan": "headline, table, fix",
            }
        ]
    )


def _idea() -> ContentIdea:
    return ContentIdea(
        id=7,
        user_id="42",
        source="notebooklm_plan",
        source_url="notebooklm://plan/fee-leak",
        status="selected",
        title="Fee leak",
        pain="Margins vanish after packaging changes.",
        angle="Audit FBA tiers before scaling PPC.",
        summary="Notebook note about hidden fee tier changes.",
        source_meta={
            "source_basis": "Notebook note",
            "mechanism": "fee tier mismatch",
            "first_frame_text": "FEE LEAK",
            "visual_proof": "fee table",
        },
        fingerprint="fee leak",
        created_at="",
        updated_at="",
    )


class FakeKieTextClient:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls = []

    def is_configured(self) -> bool:
        return True

    def complete(self, *, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        return self.answer


class FailingNotebookLM:
    def ask(self, *args, **kwargs):
        raise AssertionError("NotebookLM should not be called")


class NotebookLMAnswer:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls = 0

    def ask(self, *args, **kwargs):
        self.calls += 1
        return self


class FailingKieTextClient:
    def is_configured(self) -> bool:
        return True

    def complete(self, *, system: str, user: str) -> str:
        raise ValueError("model unsupported")
