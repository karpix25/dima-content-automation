from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .storage import ScriptRecord


@dataclass(frozen=True)
class VisualAssetSet:
    cover_path: Path
    broll_paths: list[Path]


def generate_post_heygen_assets(
    *,
    record: ScriptRecord,
    output_dir: Path,
    broll_count: int,
) -> VisualAssetSet:
    output_dir.mkdir(parents=True, exist_ok=True)
    size = (1080, 1920) if record.format == "short" else (1920, 1080)
    cover_path = output_dir / f"cover_{record.id}.png"
    _render_card(
        cover_path,
        size=size,
        title=record.hook or record.title or "Key idea",
        subtitle=record.trigger or record.angle,
        footer=record.cta,
        accent=(235, 201, 124),
    )
    broll_paths: list[Path] = []
    for index, text in enumerate(_broll_texts(record)[:broll_count], start=1):
        path = output_dir / f"broll_{record.id}_{index}.png"
        _render_card(
            path,
            size=size,
            title=text,
            subtitle=record.title,
            footer=record.cta,
            accent=(88, 168, 121) if index % 2 else (120, 150, 190),
        )
        broll_paths.append(path)
    return VisualAssetSet(cover_path=cover_path, broll_paths=broll_paths)


def _broll_texts(record: ScriptRecord) -> list[str]:
    candidates = [
        record.trigger,
        record.angle,
        record.why_it_works,
        record.source_basis,
        record.cta,
    ]
    voiceover_sentences = re.split(r"(?<=[.!?])\s+", record.voiceover or "")
    candidates.extend(voiceover_sentences[:4])
    return [_clean_text(item) for item in candidates if _clean_text(item)]


def _render_card(
    path: Path,
    *,
    size: tuple[int, int],
    title: str,
    subtitle: str,
    footer: str,
    accent: tuple[int, int, int],
) -> None:
    width, height = size
    image = Image.new("RGB", size, (32, 35, 39))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, int(height * 0.12)), fill=accent)
    draw.rectangle((0, int(height * 0.88), width, height), fill=accent)

    margin = int(width * 0.075)
    title_font = _font(max(44, int(width * 0.07)))
    subtitle_font = _font(max(28, int(width * 0.034)))
    footer_font = _font(max(24, int(width * 0.03)))

    title_lines = _wrap(title.upper(), max_chars=18 if width < height else 30)
    title_y = int(height * 0.28)
    for line in title_lines[:5]:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        draw.text(
            ((width - (bbox[2] - bbox[0])) / 2, title_y),
            line,
            font=title_font,
            fill=(250, 250, 246),
        )
        title_y += int((bbox[3] - bbox[1]) * 1.28)

    subtitle = _clean_text(subtitle)
    if subtitle:
        subtitle_y = min(title_y + int(height * 0.05), int(height * 0.68))
        for line in _wrap(subtitle, max_chars=28 if width < height else 48)[:4]:
            bbox = draw.textbbox((0, 0), line, font=subtitle_font)
            draw.text(
                ((width - (bbox[2] - bbox[0])) / 2, subtitle_y),
                line,
                font=subtitle_font,
                fill=(230, 234, 238),
            )
            subtitle_y += int((bbox[3] - bbox[1]) * 1.45)

    footer = _clean_text(footer)
    if footer:
        footer_lines = _wrap(footer, max_chars=26 if width < height else 54)
        footer_y = int(height * 0.91)
        for line in footer_lines[:2]:
            bbox = draw.textbbox((0, 0), line, font=footer_font)
            draw.text(
                ((width - (bbox[2] - bbox[0])) / 2, footer_y),
                line,
                font=footer_font,
                fill=(31, 35, 39),
            )
            footer_y += int((bbox[3] - bbox[1]) * 1.35)

    image.save(path)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _wrap(value: str, *, max_chars: int) -> list[str]:
    words = _clean_text(value).split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) > max_chars and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines or [""]


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()
