from __future__ import annotations


def video_size_for_format(format_name: str) -> tuple[int, int]:
    return (1920, 1080) if format_name == "youtube" else (1080, 1920)


def is_horizontal_format(format_name: str) -> bool:
    return format_name == "youtube"


def vizard_platforms_for_ratio(ratio_of_clip: int) -> tuple[str, ...]:
    return ("youtube",) if ratio_of_clip == 4 else ("shorts", "reels")
