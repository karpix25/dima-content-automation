from content_automation.notebooklm_script_attempts import (
    ScriptGenerationAttemptStats,
    merge_attempt_stats,
    retry_correction_for_stats,
    script_generation_failure_message,
)


def test_script_generation_failure_message_explains_invalid_json():
    stats = ScriptGenerationAttemptStats(parse_errors=["response does not contain valid JSON"])

    message = script_generation_failure_message(stats)

    assert "невалидным JSON" in message
    assert "не в размере пачки" in message


def test_script_generation_failure_message_explains_rejections():
    stats = ScriptGenerationAttemptStats(parsed_items=2)
    stats.reject("duplicate")
    stats.reject("word_budget")

    message = script_generation_failure_message(stats)

    assert "похожая тема уже есть" in message
    assert "не попал в длину озвучки" in message


def test_retry_correction_prioritizes_json_parse_error():
    stats = ScriptGenerationAttemptStats(parse_errors=["bad json"])

    correction = retry_correction_for_stats(stats, reject_cyrillic=False)

    assert "not valid JSON" in correction
    assert "Return ONLY a raw JSON array" in correction


def test_merge_attempt_stats_combines_counts():
    first = ScriptGenerationAttemptStats(parsed_items=1, accepted_items=0, parse_errors=["bad json"])
    second = ScriptGenerationAttemptStats(parsed_items=2, accepted_items=1)
    second.reject("duplicate")

    merged = merge_attempt_stats([first, second])

    assert merged.parsed_items == 3
    assert merged.accepted_items == 1
    assert merged.parse_errors == ["bad json"]
    assert merged.rejected["duplicate"] == 1
