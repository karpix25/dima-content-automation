from __future__ import annotations

from .storage import ScriptRecord


def build_turan_infographic_prompt(
    *,
    record: ScriptRecord,
    bullets: list[str],
    cta_text: str | None = None,
    has_references: bool = False,
) -> str:
    title = clean_prompt_text(record.hook or record.title or "Main insight")
    subtitle = clean_prompt_text(record.angle or record.trigger or record.source_basis)
    items = [clean_prompt_text(item) for item in bullets[:7] if clean_prompt_text(item)]
    final_thought = clean_prompt_text(record.why_it_works or record.source_basis or record.cta)
    cta = clean_prompt_text(cta_text or record.cta or "Follow for more")
    reference_rule = (
        "Use the uploaded face/style reference images to keep the author cutout and visual style consistent. "
        "Do not copy old text from references; replace all text with the exact text below. "
        if has_references
        else ""
    )
    return (
        "Create a finished vertical Instagram/Reels business infographic card, 9:16. "
        f"{reference_rule}"
        "Use this exact text on the card, do not invent new facts and do not rewrite it. "
        f"Top headline text: {title}. "
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
