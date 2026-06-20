from content_automation.storage import ScriptRecord
from content_automation.turan_infographic_prompt import build_turan_infographic_prompt


def test_turan_infographic_prompt_uses_original_design_with_dima_text():
    prompt = build_turan_infographic_prompt(
        record=_record(),
        bullets=["Fix SQP bottlenecks", "Reduce wasted PPC spend"],
        cta_text="Book a Dima audit",
        has_references=True,
    )

    assert "#EBC97C" in prompt
    assert "off-white/milky rounded rectangle block" in prompt
    assert "Montserrat" in prompt
    assert "realistic cutout sticker of the author" in prompt
    assert "bottom 22% of the 9:16 frame" in prompt
    assert "right 16% of the frame" in prompt
    assert "CTA window above the bottom safe zone" in prompt
    assert "Fix SQP bottlenecks" in prompt
    assert "Book a Dima audit" in prompt
    assert "тендеры" not in prompt.lower()


def test_turan_infographic_prompt_uses_configured_language():
    prompt = build_turan_infographic_prompt(
        record=_record(),
        bullets=["Fix SQP bottlenecks"],
        content_language="ru",
    )

    assert "All viewer-facing text must be in natural Russian" in prompt


def test_turan_infographic_prompt_filters_internal_source_copy_for_russian_card():
    record = _record(
        title="Слив бюджета в PPC",
        hook="Слив бюджета в PPC не пробьет стеклянный потолок выручки.",
        trigger="Продавец уперся в потолок выручки и пытается разогнать PPC.",
        angle="Сначала проверь конверсию карточки, потом увеличивай рекламный бюджет.",
        cta="",
        source_basis="Презентация lovepdf (8).pdf, слайды 122-123. Скрипт разрушает популярное заблуждение.",
    )

    prompt = build_turan_infographic_prompt(record=record, bullets=[], content_language="ru")

    assert "Follow for more" not in prompt
    assert "Сохрани разбор" in prompt
    assert "lovepdf" not in prompt
    assert ".pdf" not in prompt
    assert "слайды" not in prompt.lower()
    assert "Скрипт разрушает" not in prompt
    assert 'H1/top headline exact text: "Слив бюджета в PPC не пробьет стеклянный потолок"' in prompt
    assert "Revenue growth means nothing" not in prompt
    assert "PPC не лечит слабую конверсию" in prompt


def test_turan_infographic_prompt_omits_english_internal_fields_for_russian_card():
    record = _record(
        title="Скрытая прибыль через Amazon Attribution",
        hook="Вы сливаете маржу на внешний трафик, потому что не забираете кэшбэк от самого Амазона.",
        trigger="scaling external traffic without utilizing marketplace reimbursement programs",
        angle="Раскрываем механику Amazon Attribution для возврата рекламных расходов.",
        cta="Внедряем такие системы масштабирования на наставничестве.",
        why_it_works="Targets a very specific operational inefficiency for existing sellers.",
        source_basis="lovepdf (8).pdf, slide 112",
        raw={
            "mechanism": "Amazon Attribution tracks external traffic and refunds a portion of the referral fee",
            "visual_proof": "Скриншот дашборда Amazon Attribution с начисленным бонусом.",
        },
    )

    prompt = build_turan_infographic_prompt(
        record=record,
        bullets=[
            record.trigger,
            record.why_it_works,
            "Сначала проверь маржу, потом разгоняй трафик.",
        ],
        content_language="ru",
    )

    assert "scaling external traffic" not in prompt
    assert "Targets a very specific" not in prompt
    assert "tracks external traffic" not in prompt
    assert "Сначала проверь маржу" in prompt
    assert "Скриншот дашборда Amazon Attribution" in prompt


def _record(**overrides) -> ScriptRecord:
    values = {
        "title": "Margin trap",
        "angle": "Profit angle",
        "hook": "Revenue is not profit",
        "trigger": "Cash conversion",
        "voiceover": "Your revenue can grow while your cash disappears.",
        "cta": "Check contribution margin.",
        "why_it_works": "Sharp seller pain.",
        "source_basis": "NotebookLM notes.",
    }
    raw = values.pop("raw", {})
    values.update(overrides)
    raw = values.pop("raw", raw)
    return ScriptRecord(
        id=1,
        user_id="42",
        format="short",
        status="approved",
        title=values["title"],
        angle=values["angle"],
        hook=values["hook"],
        trigger=values["trigger"],
        voiceover=values["voiceover"],
        cta=values["cta"],
        why_it_works=values["why_it_works"],
        source_basis=values["source_basis"],
        raw=raw,
    )
