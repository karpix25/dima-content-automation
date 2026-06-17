from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .content_language import viewer_text_language_instruction
from .kie_image import KieImageClient
from .storage import ScriptRecord
from .video_geometry import is_horizontal_format, video_size_for_format


@dataclass(frozen=True)
class VisualAssetSet:
    cover_path: Path
    broll_paths: list[Path]

@dataclass(frozen=True)
class VisualAssetRequest:
    path: Path
    prompt: str
    size: tuple[int, int]
    aspect_ratio: str
    title: str
    subtitle: str
    footer: str
    accent: tuple[int, int, int]


def generate_post_heygen_assets(
    *,
    record: ScriptRecord,
    output_dir: Path,
    broll_count: int,
    kie_client: KieImageClient | None = None,
    reference_paths: list[Path] | None = None,
    face_reference_paths: list[Path] | None = None,
    style_reference_paths: list[Path] | None = None,
    target_size: tuple[int, int] | None = None,
    content_language: str = "auto",
) -> VisualAssetSet:
    output_dir.mkdir(parents=True, exist_ok=True)
    size = target_size or video_size_for_format(record.format)
    cover_path = output_dir / f"cover_{record.id}.png"
    face_paths = face_reference_paths or []
    style_paths = style_reference_paths or []
    legacy_paths = reference_paths or []
    all_references = [*face_paths, *style_paths, *legacy_paths]
    has_references = bool(all_references)
    cover_request = VisualAssetRequest(
        path=cover_path,
        prompt=_cover_prompt(
            record,
            has_references=has_references,
            has_face_reference=bool(face_paths),
            has_style_references=bool(style_paths or legacy_paths),
            orientation=_orientation_label(size),
            content_language=content_language,
        ),
        size=size,
        aspect_ratio=_aspect_ratio_label(size),
        title=record.hook or record.title or "Key idea",
        subtitle=record.trigger or record.angle,
        footer=record.cta,
        accent=(235, 201, 124),
    )
    broll_texts = _broll_texts(record)[:broll_count]
    broll_paths: list[Path] = []
    for index, text in enumerate(broll_texts, start=1):
        path = output_dir / f"broll_{record.id}_{index}.png"
        broll_paths.append(path)
    broll_requests = [
        VisualAssetRequest(
            path=path,
            prompt=_broll_prompt(record, text, has_references=has_references, content_language=content_language),
            size=size,
            aspect_ratio=_aspect_ratio_label(size),
            title=text,
            subtitle=record.title,
            footer=record.cta,
            accent=(88, 168, 121) if index % 2 else (120, 150, 190),
        )
        for index, (path, text) in enumerate(zip(broll_paths, broll_texts), start=1)
    ]
    _generate_requests(kie_client=kie_client, requests=[cover_request, *broll_requests], reference_paths=all_references)
    return VisualAssetSet(cover_path=cover_path, broll_paths=broll_paths)


def _generate_requests(*, kie_client: KieImageClient | None, requests: list[VisualAssetRequest], reference_paths: list[Path]) -> None:
    input_urls = kie_client.upload_references(reference_paths) if kie_client and kie_client.is_configured() else []
    if not requests:
        return
    _generate_or_render(kie_client=kie_client, request=requests[0], input_urls=input_urls)
    broll_requests = requests[1:]
    if len(broll_requests) <= 1 or not (kie_client and kie_client.is_configured()):
        for request in broll_requests:
            _generate_or_render(kie_client=kie_client, request=request, input_urls=input_urls)
        return
    with ThreadPoolExecutor(max_workers=min(3, len(broll_requests))) as executor:
        list(
            executor.map(
                lambda request: _generate_or_render(kie_client=kie_client, request=request, input_urls=input_urls),
                broll_requests,
            )
        )


def _generate_or_render(*, kie_client: KieImageClient | None, request: VisualAssetRequest, input_urls: list[str]) -> None:
    if kie_client and kie_client.is_configured():
        generated = kie_client.generate_image_from_uploaded_refs(
            prompt=request.prompt,
            output_path=request.path,
            input_urls=input_urls,
            aspect_ratio=request.aspect_ratio,
        )
        if generated and generated.exists():
            return
    _render_card(
        request.path,
        size=request.size,
        title=request.title,
        subtitle=request.subtitle,
        footer=request.footer,
        accent=request.accent,
    )


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


def _cover_prompt(
    record: ScriptRecord,
    *,
    has_references: bool = False,
    has_face_reference: bool = False,
    has_style_references: bool = False,
    orientation: str = "vertical 9:16",
    content_language: str = "auto",
) -> str:
    if not has_references:
        reference_rule = ""
    else:
        face_rule = (
            "The first uploaded reference image(s) are AUTHOR FACE references. The person in the final cover must match that face identity, age range, facial structure, and general appearance. "
            "Do not invent a different presenter and do not use people from style references as the author. "
            if has_face_reference
            else ""
        )
        style_rule = (
            "The remaining uploaded reference images are STYLE ONLY references. Use them as a thumbnail style board: match their layout logic, visual hierarchy, "
            "large-text rhythm, bold numbers, color energy, contrast, spacing, face placement, and social-thumbnail composition. "
            if has_style_references
            else ""
        )
        reference_rule = (
        "Uploaded images are mandatory references, not loose inspiration. "
            f"{face_rule}"
            f"{style_rule}"
        "The result must feel like the same thumbnail system as the references, adapted to the new topic. "
        "Do not copy old text, logos, exact numbers, old faces, or identities from style references. "
        )
    return (
        f"Create a premium {orientation} cover frame for a business video. "
        f"{reference_rule}"
        f"{viewer_text_language_instruction(content_language)} "
        "Prioritize social-media thumbnail performance over cinematic poster style. "
        "Use a clear face + oversized readable headline/numbers composition when it fits the references. "
        "High contrast, sharp composition, simple visual story, instantly understandable at phone size. "
        "No logos, no watermarks, no fake platform UI. Replace all reference text with new exact topic text. "
        f"Main cover headline: {_clean_text(record.hook or record.title)}. "
        f"Supporting idea: {_clean_text(record.trigger or record.angle)}. "
        f"Context: {_clean_text(record.source_basis or record.voiceover)[:900]}."
    )


def _broll_prompt(record: ScriptRecord, text: str, *, has_references: bool = False, content_language: str = "auto") -> str:
    reference_rule = (
        "Use uploaded style references as a style board for color, contrast, hierarchy, spacing, and composition. "
        "Do not copy their old text, logos, numbers, faces, or identities. "
        if has_references
        else ""
    )
    orientation = "horizontal 16:9" if is_horizontal_format(record.format) else "vertical 9:16"
    return (
        f"Create a premium {orientation} cutaway image for a business explainer video. "
        f"{reference_rule}"
        f"{viewer_text_language_instruction(content_language)} "
        "This is a visual interruption after an AI avatar segment: cinematic, realistic, clean, high contrast. "
        "No logos, no watermarks, no UI, no fake screenshots. "
        "If text is present, it must be large and readable, minimal, not crowded. "
        f"Cutaway message: {_clean_text(text)}. "
        f"Video topic: {_clean_text(record.title or record.hook)}. "
        f"Script context: {_clean_text(record.voiceover)[:900]}."
    )


def _orientation_label(size: tuple[int, int]) -> str:
    width, height = size
    if width == height:
        return "square 1:1"
    if width > height:
        return "horizontal 16:9"
    return "vertical 9:16"


def _aspect_ratio_label(size: tuple[int, int]) -> str:
    width, height = size
    if width == height:
        return "1:1"
    return "16:9" if width > height else "9:16"


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
