from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from content_automation.config import Settings
from content_automation.idea_bank import IdeaBank
from content_automation.storage import Storage
from content_automation.web_ideas import build_ideas_router


def test_notebooklm_ideas_endpoint_uses_user_language(tmp_path: Path):
    storage = Storage(tmp_path / "app.sqlite3")
    idea_bank = IdeaBank(tmp_path / "app.sqlite3")
    storage.set_setting("42", "notebook_id", "notebook-1")
    storage.set_setting("42", "content_language", "ru")
    calls = []

    class FakeNotebookLM:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            calls.append(question)
            return SimpleNamespace(
                answer='[{"title":"Риск Buy Box","pain":"Маржа падает","angle":"Проверь оффер","summary":"Заметка"}]'
            )

    app = FastAPI()
    app.include_router(
        build_ideas_router(
            storage=storage,
            idea_bank=idea_bank,
            settings=_settings(tmp_path),
            notebooklm=FakeNotebookLM(),
        )
    )
    client = TestClient(app)

    response = client.post("/api/ideas/notebooklm", json={"user_id": "42", "count": 5})

    assert response.status_code == 200
    assert response.json()["inserted"] == 1
    assert response.json()["ideas"][0]["source"] == "notebooklm"
    assert "natural Russian" in calls[0]


def test_notebooklm_plan_endpoint_creates_monthly_plan(tmp_path: Path):
    storage = Storage(tmp_path / "app.sqlite3")
    idea_bank = IdeaBank(tmp_path / "app.sqlite3")
    storage.set_setting("42", "notebook_id", "notebook-1")
    storage.set_setting("42", "content_language", "ru")
    calls = []

    class FakeNotebookLM:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            calls.append(question)
            return SimpleNamespace(
                answer=(
                    '{"plan":[{"day":1,"pillar":"Маржа","format":"vertical_short",'
                    '"title":"Утечка маржи","pain":"Прибыль исчезает","angle":"Проверь FBA tier",'
                    '"summary":"Серия начинается с самой дорогой ошибки.",'
                    '"visual_note":"Показать коробку и таблицу комиссий","source_basis":"Заметка"}]}'
                )
            )

    app = FastAPI()
    app.include_router(
        build_ideas_router(
            storage=storage,
            idea_bank=idea_bank,
            settings=_settings(tmp_path),
            notebooklm=FakeNotebookLM(),
        )
    )
    client = TestClient(app)

    response = client.post("/api/ideas/notebooklm-plan", json={"user_id": "42", "count": 30})

    assert response.status_code == 200
    payload = response.json()
    assert payload["inserted"] == 1
    assert payload["ideas"][0]["source"] == "notebooklm_plan"
    assert payload["ideas"][0]["source_meta"]["visual_note"] == "Показать коробку и таблицу комиссий"
    assert "senior social media producer" in calls[0]
    assert "natural Russian" in calls[0]


def test_notebooklm_plan_extend_endpoint_avoids_existing_topics(tmp_path: Path):
    storage = Storage(tmp_path / "app.sqlite3")
    idea_bank = IdeaBank(tmp_path / "app.sqlite3")
    storage.set_setting("42", "notebook_id", "notebook-1")
    idea_bank.add_if_new(
        "42",
        {
            "source": "notebooklm_plan",
            "source_url": "notebooklm://notebook-1/plan-day-1-fee-leak",
            "title": "Fee Leak",
            "pain": "Margins vanish",
            "angle": "Audit FBA tiers",
            "summary": "Start with money leaks.",
            "source_meta": {"day": 1, "pillar": "Margin"},
        },
    )
    calls = []

    class FakeNotebookLM:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            calls.append(question)
            return SimpleNamespace(
                answer=(
                    '{"plan":[{"day":31,"pillar":"PPC","format":"vertical_short",'
                    '"title":"Bid Waste","pain":"Ads spend too fast","angle":"Cut zombie keywords",'
                    '"summary":"Expand the plan with PPC waste.",'
                    '"visual_note":"Show PPC dashboard","source_basis":"Notebook PPC note"}]}'
                )
            )

    app = FastAPI()
    app.include_router(
        build_ideas_router(
            storage=storage,
            idea_bank=idea_bank,
            settings=_settings(tmp_path),
            notebooklm=FakeNotebookLM(),
        )
    )
    client = TestClient(app)

    response = client.post("/api/ideas/notebooklm-plan/extend", json={"user_id": "42", "count": 30})

    assert response.status_code == 200
    assert response.json()["ideas"][0]["title"] == "Bid Waste"
    assert "Do not restart the plan" in calls[0]
    assert "Fee Leak | Audit FBA tiers" in calls[0]


def test_idea_actions_reject_and_create_pending_script(tmp_path: Path):
    storage = Storage(tmp_path / "app.sqlite3")
    idea_bank = IdeaBank(tmp_path / "app.sqlite3")
    storage.set_setting("42", "notebook_id", "notebook-1")
    idea = idea_bank.add_if_new(
        "42",
        {
            "source": "notebooklm",
            "source_url": "notebooklm://notebook-1/topic",
            "title": "Buy Box trust gap",
            "pain": "Conversion is weak",
            "angle": "Audit trust signals",
            "summary": "Notebook source",
        },
    )

    class FakeNotebookLM:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            assert "Buy Box trust gap" in question
            return SimpleNamespace(
                answer=(
                    '[{"title":"Buy Box trust gap","angle":"Trust signals","hook":"Your product page can rank and still leak sales.",'
                    '"trigger":"Weak trust signals","voiceover":"'
                    + " ".join(["Amazon sellers often miss the small trust signals that decide whether a shopper clicks buy today."] * 7)
                    + '","cta":"","why_it_works":"Specific seller pain.","source_basis":"Notebook source"}]'
                )
            )

    app = FastAPI()
    app.include_router(
        build_ideas_router(
            storage=storage,
            idea_bank=idea_bank,
            settings=_settings(tmp_path),
            notebooklm=FakeNotebookLM(),
        )
    )
    client = TestClient(app)

    created = client.post(f"/api/ideas/{idea.id}/script", json={"user_id": "42", "count": 1})

    assert created.status_code == 200
    assert created.json()["title"] == "Buy Box trust gap"
    assert idea_bank.get("42", idea.id).status == "used_for_script"
    assert storage.list_scripts("42", status="pending")[0].title == "Buy Box trust gap"

    second = idea_bank.add_if_new(
        "42",
        {
            "source": "notebooklm",
            "source_url": "notebooklm://notebook-1/other",
            "title": "Other topic",
            "pain": "Slow growth",
            "angle": "Fix offer",
            "summary": "Notebook source",
        },
    )
    rejected = client.post(f"/api/ideas/{second.id}/reject", json={"user_id": "42", "count": 1})

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_auto_scripts_from_ideas_creates_pending_scripts(tmp_path: Path):
    storage = Storage(tmp_path / "app.sqlite3")
    idea_bank = IdeaBank(tmp_path / "app.sqlite3")
    storage.set_setting("42", "notebook_id", "notebook-1")
    for index in range(2):
        idea_bank.add_if_new(
            "42",
            {
                "source": "notebooklm_plan",
                "source_url": f"notebooklm://notebook-1/topic-{index}",
                "title": f"Topic {index}",
                "pain": "Conversion is weak",
                "angle": "Audit trust signals",
                "summary": "Notebook source",
            },
        )

    class FakeNotebookLM:
        def __init__(self):
            self.calls = 0

        def ask(self, question, *, notebook_url=None, notebook_id=None):
            self.calls += 1
            if self.calls == 1:
                title = "Inventory Stockout Risk"
                hook = "Your launch dies when inventory runs out too early."
                voiceover = " ".join(["Amazon operators lose ranking when stockouts interrupt launch momentum and reset organic traction."] * 7)
            else:
                title = "Packaging Fee Leak"
                hook = "Your box size quietly turns margin into extra FBA fees."
                voiceover = " ".join(["Amazon sellers protect profit by measuring packaging tiers before ordering a large production run."] * 7)
            return SimpleNamespace(
                answer=(
                    f'[{{"title":"{title}","angle":"Trust signals","hook":"{hook}",'
                    '"trigger":"Weak trust signals","voiceover":"'
                    + voiceover
                    + '","cta":"","why_it_works":"Specific seller pain.","source_basis":"Notebook source"}]'
                )
            )

    app = FastAPI()
    app.include_router(
        build_ideas_router(
            storage=storage,
            idea_bank=idea_bank,
            settings=_settings(tmp_path),
            notebooklm=FakeNotebookLM(),
        )
    )
    client = TestClient(app)

    response = client.post("/api/ideas/scripts/auto", json={"user_id": "42", "count": 30})

    assert response.status_code == 200
    assert response.json()["accepted"] == 2
    assert len(storage.list_scripts("42", status="pending")) == 2
    assert idea_bank.list_new("42") == []


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        telegram_bot_token="token",
        notebooklm_cli_command="notebooklm",
        notebooklm_backend="mcp",
        notebooklm_mcp_command="npx notebooklm-mcp@latest",
        notebooklm_mcp_timeout_seconds=30,
        notebooklm_py_storage_path=None,
        notebooklm_short_batch_size=1,
        notebooklm_keepalive_enabled=False,
        notebooklm_keepalive_interval_seconds=21600,
        notebooklm_keepalive_startup_delay_seconds=180,
        notebooklm_auth_url=None,
        notebooklm_auth_notify_chat_ids=(),
        notebooklm_auth_notify_cooldown_seconds=300,
        notebooklm_auth_start_command=None,
        notebooklm_auth_start_timeout_seconds=5,
        default_notebook_id=None,
        elevenlabs_api_key=None,
        elevenlabs_mcp_command=None,
        elevenlabs_voice_id=None,
        elevenlabs_voice_name="voice",
        elevenlabs_model_id="model",
        elevenlabs_speed=1.0,
        elevenlabs_stability=0.5,
        elevenlabs_similarity_boost=0.5,
        elevenlabs_style=0.0,
        elevenlabs_language="en",
        elevenlabs_output_directory=tmp_path,
        video_output_directory=tmp_path,
        video_keep_days=1,
        heygen_api_key=None,
        heygen_api_base_url="https://api.heygen.com",
        heygen_upload_base_url="https://upload.heygen.com",
        heygen_private_avatars_only=True,
        heygen_aspect_ratio="9:16",
        heygen_resolution="720p",
        heygen_output_format="mp4",
        heygen_video_poll_seconds=1,
        heygen_video_timeout_seconds=1,
        data_dir=tmp_path,
        miniapp_url=None,
        miniapp_require_telegram_auth=False,
        web_host="0.0.0.0",
        web_port=8000,
        turan_api_base_url=None,
        turan_api_telegram_id=None,
        post_heygen_visuals_enabled=True,
        post_heygen_cover_seconds=0.1,
        post_heygen_broll_count=3,
        post_heygen_broll_seconds=1.2,
        kie_api_key=None,
        kie_base_url="https://api.kie.ai",
        kie_upload_base_url="https://kie.test",
        kie_image_model="gpt-image-2",
        kie_image_aspect_ratio="9:16",
        kie_image_resolution="1K",
        kie_poll_timeout_seconds=1,
        kie_poll_interval_seconds=1,
        kie_create_task_max_attempts=1,
        kie_create_task_retry_delay_seconds=1,
        montage_renderer="auto",
        hyperframes_project_dir=None,
        remotion_project_dir=None,
        montage_render_timeout_seconds=60,
        montage_max_scenes=8,
        deepgram_api_key=None,
        deepgram_api_base_url="https://api.deepgram.com",
        deepgram_model="nova-2",
        deepgram_language="en",
        deepgram_timeout_seconds=30,
        vizard_api_key=None,
        vizard_api_base_url="https://vizard.test",
        vizard_poll_seconds=5,
        vizard_timeout_seconds=60,
        vizard_request_timeout_seconds=10,
        scrapecreators_api_key=None,
        scrapecreators_api_base_url="https://api.scrapecreators.com",
        scrapecreators_mcp_url="https://api.scrapecreators.com/mcp",
        scrapecreators_request_timeout_seconds=10,
        scrapecreators_reddit_subreddits=("AmazonFBA",),
        scrapecreators_reddit_timeframe="week",
        scrapecreators_trend_limit=5,
    )
