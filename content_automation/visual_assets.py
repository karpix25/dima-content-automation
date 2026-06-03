from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .kie_image import KieImageClient
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
    kie_client: KieImageClient | None = None,
    reference_paths: list[Path] | None = None,
) -> VisualAssetSet:
    output_dir.mkdir(parents=True, exist_ok=True)
    size = (1080, 1920) if record.format == "short" else (1920, 1080)
    cover_path = output_dir / f"cover_{record.id}.png"
    _generate_or_render(
        kie_client=kie_client,
        path=cover_path,
        prompt=_cover_prompt(record, has_references=bool(reference_paths)),
        reference_paths=reference_paths or [],
        size=size,
        title=record.hook or record.title or "Key idea",
        subtitle=record.trigger or record.angle,
        footer=record.cta,
        accent=(235, 201, 124),
    )
    broll_paths: list[Path] = []
    for index, text in enumerate(_broll_texts(record)[:broll_count], start=1):
        path = output_dir / f"broll_{record.id}_{index}.png"
        _generate_or_render(
            kie_client=kie_client,
            path=path,
            prompt=_broll_prompt(record, text, has_references=bool(reference_paths)),
            reference_paths=reference_paths or [],
            size=size,
            title=text,
            subtitle=record.title,
            footer=record.cta,
            accent=(88, 168, 121) if index % 2 else (120, 150, 190),
        )
        broll_paths.append(path)
    return VisualAssetSet(cover_path=cover_path, broll_paths=broll_paths)


def _generate_or_render(
    *,
    kie_client: KieImageClient | None,
    path: Path,
    prompt: str,
    reference_paths: list[Path],
    size: tuple[int, int],
    title: str,
    subtitle: str,
    footer: str,
    accent: tuple[int, int, int],
) -> None:
    if kie_client and kie_client.is_configured():
        generated = kie_client.generate_image(prompt=prompt, output_path=path, reference_paths=reference_paths)
        if generated and generated.exists():
            return
    _render_card(path, size=size, title=title, subtitle=subtitle, footer=footer, accent=accent)


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


def _cover_prompt(record: ScriptRecord, *, has_references: bool = False) -> str:
    reference_rule = (
        "Uploaded images are mandatory references, not loose inspiration. "
        "If a face/person reference is present, use it only for the author's identity and likeness. "
        "Use the uploaded thumbnail/style references as a style board: match their layout logic, visual hierarchy, "
        "large-text rhythm, bold numbers, color energy, contrast, spacing, face placement, and social-thumbnail composition. "
        "The result must feel like the same thumbnail system as the references, adapted to the new topic. "
        "Do not copy old text, logos, exact numbers, old faces, or identities from style references. "
        if has_references
        else ""
    )
    return (
        "Create a premium vertical 9:16 cover frame for a business short video. "
        f"{reference_rule}"
        "Prioritize social-media thumbnail performance over cinematic poster style. "
        "Use a clear face + oversized readable headline/numbers composition when it fits the references. "
        "High contrast, sharp composition, simple visual story, instantly understandable at phone size. "
        "No logos, no watermarks, no fake platform UI. Replace all reference text with new exact topic text. "
        f"Main cover headline: {_clean_text(record.hook or record.title)}. "
        f"Supporting idea: {_clean_text(record.trigger or record.angle)}. "
        f"Context: {_clean_text(record.source_basis or record.voiceover)[:900]}."
    )


def _broll_prompt(record: ScriptRecord, text: str, *, has_references: bool = False) -> str:
    reference_rule = (
        "Use uploaded style references as a style board for color, contrast, hierarchy, spacing, and composition. "
        "Do not copy their old text, logos, numbers, faces, or identities. "
        if has_references
        else ""
    )
    return (
        "Create a premium vertical 9:16 cutaway image for a business explainer video. "
        f"{reference_rule}"
        "This is a visual interruption after an AI avatar segment: cinematic, realistic, clean, high contrast. "
        "No logos, no watermarks, no UI, no fake screenshots. "
        "If text is present, it must be large and readable, minimal, not crowded. "
        f"Cutaway message: {_clean_text(text)}. "
        f"Video topic: {_clean_text(record.title or record.hook)}. "
        f"Script context: {_clean_text(record.voiceover)[:900]}."
    )


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
