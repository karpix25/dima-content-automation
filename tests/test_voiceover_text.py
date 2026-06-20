from pathlib import Path

from content_automation.storage import Storage
from content_automation.voiceover_text import normalize_voiceover_for_tts


def test_normalize_voiceover_for_tts_writes_russian_numbers_as_words():
    text = normalize_voiceover_for_tts(
        "За 5 секунд покажи x5 рост, $1M выручки, 15% бонуса и 2 000 единиц товара."
    )

    assert "пять секунд" in text
    assert "в пять раз рост" in text
    assert "один миллион долларов" in text
    assert "пятнадцать процентов" in text
    assert "две тысячи единиц" in text
    assert "5" not in text
    assert "$1M" not in text


def test_normalize_voiceover_for_tts_handles_multiplier_ranges():
    text = normalize_voiceover_for_tts("Агрегаторы покупают бренды за х3-х5 от годовой прибыли.")

    assert "за три-пять раз от годовой прибыли" in text
    assert "за от" not in text
    assert "х3" not in text


def test_normalize_voiceover_for_tts_writes_english_numbers_as_words():
    text = normalize_voiceover_for_tts("Recover $2.5k from 12% wasted PPC and grow x3.")

    assert "two thousand five hundred dollars" in text
    assert "twelve percent" in text
    assert "three times" in text


def test_normalize_voiceover_for_tts_keeps_dollar_cents():
    text = normalize_voiceover_for_tts("Raise the price from $19.99 to $21.50.")

    assert "nineteen dollars ninety nine cents" in text
    assert "twenty one dollars fifty cents" in text


def test_storage_normalizes_voiceover_before_saving(tmp_path: Path):
    storage = Storage(tmp_path / "scripts.sqlite3")

    record = storage.add_script(
        "42",
        "short",
        {
            "title": "Тест",
            "voiceover": "Запусти план на 30 дней и добери 10 сценариев.",
        },
    )

    assert record.voiceover == "Запусти план на тридцать дней и добери десять сценариев."
