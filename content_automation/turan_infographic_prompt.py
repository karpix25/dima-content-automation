from __future__ import annotations

from .storage import ScriptRecord


def build_turan_infographic_prompt(
    *,
    record: ScriptRecord,
    bullets: list[str],
    cta_text: str | None = None,
    has_references: bool = False,
    has_face_references: bool = False,
    has_design_references: bool = False,
) -> str:
    title = limit_chars(record.hook or record.title or "Main insight", 64)
    subtitle = limit_chars(record.angle or record.trigger or record.source_basis, 86)
    items = [limit_chars(item, 86) for item in bullets[:7] if clean_prompt_text(item)]
    final_thought = clean_prompt_text(record.why_it_works or record.source_basis or record.cta)
    cta = clean_prompt_text(cta_text or record.cta or "Follow for more")
    reference_rule = reference_instruction(has_references, has_face_references, has_design_references)
    return (
        "Create a finished vertical Instagram/Reels business infographic card, 9:16. "
        f"{reference_rule}"
        "Use this exact text on the card, do not invent new facts and do not rewrite it. "
        "Text fit rules: H1 max 64 characters, H2/subtitle max 86 characters, no cropped words, no broken words, "
        "no ellipses, no text outside safe margins; if needed reduce font size while keeping hierarchy. "
        f"H1/top headline exact text: {title}. "
        f"H2/subtitle exact text: {subtitle}. "
        f"Main block items: {'; '.join(items)}. "
        f"Final thought: {final_thought}. "
        f"CTA window text: {cta}. "
        "Design style: one solid warm golden-sand background, exact color #EBC97C, no gradient and no shade shift. "
        "Minimal premium business infographic, no logos, no watermarks, no fake UI, no extra colors, no decorative clutter. "
        "At the top, place a large black headline directly on the gold background. "
        "Below it, place one large off-white/milky rounded rectangle block with the main text. "
        "At the bottom, place a separate off-white CTA window. "
        "Use strictly Montserrat or Montserrat-like geometric sans-serif: headline ExtraBold/Black, body SemiBold, CTA ExtraBold. "
        "Do not use serif, handwritten, condensed, decorative, Arial-like, or Instagram UI fonts. "
        "Add a realistic cutout sticker of the author: man with dark hair, thick dark beard, expressive eyebrows, "
        "confident or engaged expression, pointing at the main block or CTA, 18-22% of frame height. "
        "The author must not cover important text. "
        "Text must be large, clean, readable, aligned, and not overloaded. "
        "The final image must look like a polished Turan five-second infographic card, ready for video."
    )


def clean_prompt_text(value: str | None) -> str:
    return " ".join((value or "").replace("\n", " ").split())


def limit_chars(value: str | None, limit: int) -> str:
    clean = clean_prompt_text(value)
    if len(clean) <= limit:
        return clean
    words: list[str] = []
    for word in clean.split():
        candidate = " ".join([*words, word]).strip()
        if len(candidate) > limit:
            break
        words.append(word)
    return " ".join(words) or clean[:limit].rstrip()


def reference_instruction(has_references: bool, has_face_references: bool, has_design_references: bool) -> str:
    if not has_references:
        return ""
    parts: list[str] = []
    if has_face_references:
        parts.append("Use the uploaded face reference image only for author identity and face likeness.")
    if has_design_references:
        parts.append("Use uploaded infographic design references only for layout, hierarchy, spacing, visual rhythm, and composition style.")
    parts.append("Do not copy old text, logos, numbers, faces, or identities from design references; replace all text with the exact text below.")
    return " ".join(parts) + " "
