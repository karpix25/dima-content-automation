from types import SimpleNamespace

from content_automation.topic_dedupe import (
    build_exclusion_context,
    script_payload_is_duplicate,
    script_topic_fingerprint,
)


def test_topic_fingerprint_prefers_explicit_model_field():
    payload = {
        "title": "Generic title",
        "topic_fingerprint": "PPC waste + cash-flow leak + scaling seller + stop hidden margin loss",
    }

    assert script_topic_fingerprint(payload) == "ppc waste cash flow leak scaling stop hidden margin loss"


def test_duplicate_detection_catches_same_fingerprint_with_different_hook():
    existing = [
        SimpleNamespace(
            title="Your ads look profitable while cash disappears",
            hook="This PPC metric is lying to you.",
            voiceover="Old script.",
            topic_fingerprint="ppc waste cash flow leak scaling seller",
            raw={},
        )
    ]
    payload = {
        "title": "The campaign is not the problem",
        "hook": "Your best-looking ad report can still drain the bank account.",
        "voiceover": "New wording.",
        "topic_fingerprint": "PPC waste + cash-flow leak + scaling seller + margin loss",
    }

    assert script_payload_is_duplicate(payload, existing, []) is True


def test_exclusion_context_includes_fingerprint():
    records = [
        SimpleNamespace(
            title="Inventory is eating profit",
            hook="You can run out of cash before you run out of stock.",
            voiceover="",
            topic_fingerprint="inventory cash conversion margin leak",
            raw={},
        )
    ]

    context = build_exclusion_context(records)

    assert "Inventory is eating profit" in context
    assert "inventory cash conversion margin leak" in context
