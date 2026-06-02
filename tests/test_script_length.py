from content_automation.script_length import (
    count_spoken_words,
    length_instruction,
    vertical_word_budget,
    youtube_word_budget,
)


def test_count_spoken_words_handles_contractions_and_numbers():
    assert count_spoken_words("Amazon's 2-mm mistake costs $1 per unit.") == 7


def test_vertical_original_keeps_existing_short_range():
    budget = vertical_word_budget("original")

    assert budget.min_words == 80
    assert budget.max_words == 120
    assert budget.target_seconds is None


def test_vertical_fixed_duration_uses_spoken_wpm_budget():
    budget = vertical_word_budget("60")

    assert budget.target_words == 150
    assert budget.min_words == 132
    assert budget.max_words == 168
    assert budget.target_seconds == 60


def test_youtube_budget_uses_minutes_setting():
    budget = youtube_word_budget(12)

    assert budget.target_words == 1800
    assert budget.min_words == 1656
    assert budget.max_words == 1944
    assert "12 min horizontal YouTube" in length_instruction(budget)
