import asyncio
from pathlib import Path
from types import SimpleNamespace

from content_automation import kie_idea_pipeline
from content_automation.idea_bank import ContentIdea, IdeaBank
from content_automation.storage import ScriptRecord, Storage


def test_kie_idea_pipeline_passes_notebooklm_fallback_dependencies(tmp_path: Path, monkeypatch):
    storage = Storage(tmp_path / "scripts.sqlite3")
    idea_bank = IdeaBank(tmp_path / "ideas.sqlite3")
    notebooklm = object()
    captured = {}

    class ConfiguredClient:
        def is_configured(self):
            return True

    async def fake_create_script_from_idea(**kwargs):
        captured.update(kwargs)
        return ScriptRecord(
            id=1,
            user_id=kwargs["user_id"],
            format="short",
            status="pending",
            title="Fee leak",
            angle="Audit FBA tiers",
            hook="Your profit leak is not PPC.",
            trigger="FBA tier changed",
            voiceover="Audit fee tiers before scaling ads.",
            cta="",
            why_it_works="Specific pain.",
            source_basis="Notebook note",
            raw={},
        )

    monkeypatch.setattr(kie_idea_pipeline, "build_kie_text_client", lambda settings: ConfiguredClient())
    monkeypatch.setattr(kie_idea_pipeline, "create_script_from_idea", fake_create_script_from_idea)

    records = asyncio.run(
        kie_idea_pipeline.create_scripts_from_ideas_with_kie(
            storage=storage,
            idea_bank=idea_bank,
            user_id="42",
            ideas=[_idea()],
            author_style="Direct expert",
            offer_context="Amazon profit audit",
            cta_mix="no CTA",
            content_language="en",
            vertical_duration_mode="original",
            settings=SimpleNamespace(),
            notebook_ref="notebook-1",
            notebooklm=notebooklm,
        )
    )

    assert len(records) == 1
    assert captured["notebook_ref"] == "notebook-1"
    assert captured["notebooklm"] is notebooklm


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
        source_meta={},
        fingerprint="fee leak",
        created_at="",
        updated_at="",
    )
