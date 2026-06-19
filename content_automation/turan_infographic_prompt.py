from __future__ import annotations

from .content_language import viewer_text_language_instruction
from .social_card_copy import build_social_card_copy
from .storage import ScriptRecord


def build_turan_infographic_prompt(
    *,
    record: ScriptRecord,
    bullets: list[str],
    cta_text: str | None = None,
    has_references: bool = False,
    has_face_references: bool = False,
    has_design_references: bool = False,
    content_language: str = "auto",
) -> str:
    copy = build_social_card_copy(record=record, bullets=bullets, cta_text=cta_text, content_language=content_language)
    reference_rule = reference_instruction(has_references, has_face_references, has_design_references)
    language_rule = viewer_text_language_instruction(content_language)
    return (
        "Create a finished vertical Instagram/Reels business infographic card, 9:16. "
        f"{reference_rule}"
        f"{language_rule} "
        "Use only the exact text below on the card. Do not invent new facts and do not rewrite it. "
        "Never place source names, PDF names, slide numbers, file names, internal notes, or prompt-analysis labels on the card. "
        "Retention strategy: this is a 5-second video card designed to take 14-16 seconds to read, encouraging pause, rewatch, and longer average view duration. "
        "Social hook rules: the card must feel like a sharp expert social post, not a document. "
        "Keep the expert meaning from the source: Amazon margins, SQP, PPC caps, Lost Keywords, operations, or cash conversion. "
        "H1 max 48 characters, 5-9 words, direct, specific, pain-first, trigger-driven, high contrast. "
        "Subtitle max 82 characters. Main block: exactly 5 expert points, max 68 characters each. "
        "No final thought paragraph, no generic motivation, no vague claims, no numbered list above 5 items. "
        "Target 52-68 visible words total so the viewer needs longer than the 5-second video to read it. "
        "Text fit rules: no cropped words, no broken words, no ellipses, no text outside safe margins; "
        "if needed reduce copy density before reducing hierarchy. "
        "Social platform safe-zone rules: design for Instagram Reels, YouTube Shorts, and TikTok overlays. "
        "Treat the bottom 22% of the 9:16 frame as covered by captions, profile controls, and navigation; keep it mostly clean golden background. "
        "Treat the right 16% of the frame as covered by like/comment/share UI; never put CTA text, bullets, headline, or the author's face there. "
        "All readable text must stay inside a central-left safe content area: x 6%-78%, y 5%-78%. "
        "Place the CTA window above the bottom safe zone, around y 72%-78%, not at the bottom edge. "
        "The author cutout may point toward the CTA, but must sit above the bottom safe zone and left of the right-side UI column. "
        f'H1/top headline exact text: "{copy.headline}". '
        f'H2/subtitle exact text: "{copy.subtitle}". '
        f"Main block items: {'; '.join(copy.items)}. "
        f'CTA window text: "{copy.cta}". '
        "Design style: one solid warm golden-sand background, exact color #EBC97C, no gradient and no shade shift. "
        "Minimal premium business infographic, no logos, no watermarks, no fake UI, no extra colors, no decorative clutter. "
        "At the top, place a large black headline directly on the gold background. "
        "Below it, place one large off-white/milky rounded rectangle block with only the 5 useful expert points. "
        "Near the lower safe area, place a separate off-white CTA window, but keep it clearly above the bottom 22% social UI zone. "
        "Use strictly Montserrat or Montserrat-like geometric sans-serif: headline ExtraBold/Black, body SemiBold, CTA ExtraBold. "
        "Do not use serif, handwritten, condensed, decorative, Arial-like, or Instagram UI fonts. "
        "Add a realistic cutout sticker of the author: man with dark hair, thick dark beard, expressive eyebrows, "
        "confident or engaged expression, pointing at the main block or CTA, 18-22% of frame height. "
        "The author must not cover important text and must not overlap the right-side or bottom social safe zones. "
        "Text must be large, clean, readable, aligned, useful, and dense enough to reward reading without looking cluttered. "
        "The final image must look like a polished Turan five-second infographic card, ready for video."
    )


def reference_instruction(has_references: bool, has_face_references: bool, has_design_references: bool) -> str:
    if not has_references:
        return ""
    parts: list[str] = []
    if has_face_references:
        parts.append("Use the uploaded face reference image only for author identity and face likeness.")
    if has_design_references:
        parts.append(
            "Use uploaded infographic design references as a style board: extract the common layout, hierarchy, spacing, visual rhythm, and composition style. "
            "If references differ, choose the cleanest least text-heavy direction."
        )
    parts.append("Do not copy old text, logos, numbers, faces, or identities from design references; replace all text with the exact text below.")
    return " ".join(parts) + " "
