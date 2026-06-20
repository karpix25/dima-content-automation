from __future__ import annotations

import re


CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
MONEY_RE = re.compile(r"\$(\d+(?:[.,]\d+)?)([kKmM])?\b")
PERCENT_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\s?%")
MULTIPLIER_RANGE_RE = re.compile(r"\b[xхХ](\d+)\s*[-–]\s*[xхХ](\d+)\b")
MULTIPLIER_RE = re.compile(r"\b[xхХ](\d+)\b")
NUMBER_RE = re.compile(r"\b\d{1,3}(?:[ ,]\d{3})+(?:[.,]\d+)?\b|\b\d+(?:[.,]\d+)?\b")


def normalize_voiceover_for_tts(text: str) -> str:
    clean = " ".join((text or "").split())
    if not clean:
        return clean
    language = "ru" if CYRILLIC_RE.search(clean) else "en"
    return _normalize_numbers(clean, language=language)


def _normalize_numbers(text: str, *, language: str) -> str:
    text = MONEY_RE.sub(lambda match: _money(match, language=language), text)
    text = PERCENT_RE.sub(lambda match: _percent(match, language=language), text)
    text = MULTIPLIER_RANGE_RE.sub(lambda match: _multiplier_range(match, language=language), text)
    text = MULTIPLIER_RE.sub(lambda match: _multiplier(match, language=language), text)
    text = NUMBER_RE.sub(lambda match: _plain_number(match, language=language), text)
    if language == "ru":
        text = re.sub(r"\bза\s+от\b", "за", text, flags=re.IGNORECASE)
    return text


def _money(match: re.Match[str], *, language: str) -> str:
    value = _parse_number(match.group(1))
    suffix = (match.group(2) or "").lower()
    multiplier = 1_000_000 if suffix == "m" else 1_000 if suffix == "k" else 1
    amount = value * multiplier
    if language == "ru":
        return _ru_money(amount)
    return _en_money(amount)


def _percent(match: re.Match[str], *, language: str) -> str:
    value = _parse_number(match.group(1))
    if language == "ru":
        return f"{_ru_number_value(value)} процентов"
    return f"{_en_number_value(value)} percent"


def _multiplier(match: re.Match[str], *, language: str) -> str:
    value = int(match.group(1))
    if language == "ru":
        return f"в {_ru_number(value)} раз"
    return f"{_en_number(value)} times"


def _multiplier_range(match: re.Match[str], *, language: str) -> str:
    start = int(match.group(1))
    end = int(match.group(2))
    if language == "ru":
        return f"{_ru_number(start)}-{_ru_number(end)} раз"
    return f"{_en_number(start)} to {_en_number(end)} times"


def _plain_number(match: re.Match[str], *, language: str) -> str:
    raw = match.group(0)
    value = _parse_number(raw)
    return _ru_number_value(value) if language == "ru" else _en_number_value(value)


def _parse_number(raw: str) -> float:
    value = raw.replace(" ", "")
    if "," in value and "." in value:
        value = value.replace(",", "")
    elif "," in value:
        parts = value.split(",")
        value = "".join(parts) if len(parts[-1]) == 3 else ".".join(parts)
    return float(value)


def _ru_money(amount: float) -> str:
    whole = int(amount)
    cents = round((amount - whole) * 100)
    words = f"{_ru_number(whole)} {_ru_plural(whole, 'доллар', 'доллара', 'долларов')}"
    if cents:
        words += f" {_ru_number(cents)} {_ru_plural(cents, 'цент', 'цента', 'центов')}"
    return words


def _en_money(amount: float) -> str:
    whole = int(amount)
    cents = round((amount - whole) * 100)
    words = f"{_en_number(whole)} {'dollar' if whole == 1 else 'dollars'}"
    if cents:
        words += f" { _en_number(cents) } {'cent' if cents == 1 else 'cents'}"
    return words


def _ru_number_value(value: float) -> str:
    if value.is_integer():
        return _ru_number(int(value))
    whole, fraction = str(value).split(".", 1)
    fraction = fraction.rstrip("0")
    return f"{_ru_number(int(whole))} целых { _ru_number(int(fraction)) } десятых"


def _en_number_value(value: float) -> str:
    if value.is_integer():
        return _en_number(int(value))
    whole, fraction = str(value).split(".", 1)
    fraction = fraction.rstrip("0")
    return f"{_en_number(int(whole))} point {' '.join(_EN_DIGITS[int(ch)] for ch in fraction)}"


_RU_UNITS = [
    "ноль",
    "один",
    "два",
    "три",
    "четыре",
    "пять",
    "шесть",
    "семь",
    "восемь",
    "девять",
]
_RU_TEENS = {
    10: "десять",
    11: "одиннадцать",
    12: "двенадцать",
    13: "тринадцать",
    14: "четырнадцать",
    15: "пятнадцать",
    16: "шестнадцать",
    17: "семнадцать",
    18: "восемнадцать",
    19: "девятнадцать",
}
_RU_TENS = {
    20: "двадцать",
    30: "тридцать",
    40: "сорок",
    50: "пятьдесят",
    60: "шестьдесят",
    70: "семьдесят",
    80: "восемьдесят",
    90: "девяносто",
}
_RU_HUNDREDS = {
    100: "сто",
    200: "двести",
    300: "триста",
    400: "четыреста",
    500: "пятьсот",
    600: "шестьсот",
    700: "семьсот",
    800: "восемьсот",
    900: "девятьсот",
}


def _ru_number(number: int) -> str:
    if number < 0:
        return "минус " + _ru_number(abs(number))
    if number < 1000:
        return _ru_under_thousand(number)
    if number < 1_000_000:
        thousands, rest = divmod(number, 1000)
        words = [_ru_thousands(thousands)]
        if rest:
            words.append(_ru_under_thousand(rest))
        return " ".join(words)
    if number < 1_000_000_000:
        millions, rest = divmod(number, 1_000_000)
        words = [f"{_ru_number(millions)} {_ru_plural(millions, 'миллион', 'миллиона', 'миллионов')}"]
        if rest:
            words.append(_ru_number(rest))
        return " ".join(words)
    return str(number)



def _ru_under_thousand(number: int) -> str:
    if number < 10:
        return _RU_UNITS[number]
    if number < 20:
        return _RU_TEENS[number]
    if number < 100:
        tens, rest = divmod(number, 10)
        return " ".join(part for part in (_RU_TENS[tens * 10], _RU_UNITS[rest] if rest else "") if part)
    hundreds, rest = divmod(number, 100)
    return " ".join(part for part in (_RU_HUNDREDS[hundreds * 100], _ru_under_thousand(rest) if rest else "") if part)


def _ru_thousands(number: int) -> str:
    if number == 1:
        prefix = "одна"
    elif number == 2:
        prefix = "две"
    else:
        prefix = _ru_number(number)
    return f"{prefix} {_ru_plural(number, 'тысяча', 'тысячи', 'тысяч')}"


def _ru_plural(number: int, one: str, few: str, many: str) -> str:
    last_two = number % 100
    last = number % 10
    if 11 <= last_two <= 14:
        return many
    if last == 1:
        return one
    if 2 <= last <= 4:
        return few
    return many


_EN_DIGITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
_EN_TEENS = {
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
}
_EN_TENS = {
    20: "twenty",
    30: "thirty",
    40: "forty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
    90: "ninety",
}


def _en_number(number: int) -> str:
    if number < 0:
        return "minus " + _en_number(abs(number))
    if number < 10:
        return _EN_DIGITS[number]
    if number < 20:
        return _EN_TEENS[number]
    if number < 100:
        tens, rest = divmod(number, 10)
        return " ".join(part for part in (_EN_TENS[tens * 10], _EN_DIGITS[rest] if rest else "") if part)
    if number < 1000:
        hundreds, rest = divmod(number, 100)
        return " ".join(part for part in (f"{_EN_DIGITS[hundreds]} hundred", _en_number(rest) if rest else "") if part)
    if number < 1_000_000:
        thousands, rest = divmod(number, 1000)
        return " ".join(part for part in (f"{_en_number(thousands)} thousand", _en_number(rest) if rest else "") if part)
    if number < 1_000_000_000:
        millions, rest = divmod(number, 1_000_000)
        return " ".join(part for part in (f"{_en_number(millions)} million", _en_number(rest) if rest else "") if part)
    return str(number)
