from __future__ import annotations


VIRAL_HOOK_PATTERNS = (
    "negative urgency",
    "curiosity gap / mechanism reveal",
    "counter-intuitive belief flip",
    "specificity slam",
    "visual pattern interrupt",
)


def viral_angle_prompt() -> str:
    return """
Viral angle requirements:
- Pick one angle: villain, counter-intuitive, curated proof, or David-vs-Goliath.
- Identify the concrete mechanism: why the problem happens or how the fix works.
- Avoid broad topics. Package each idea around a conflict, hidden cost, diagnostic, or proof story.
- Prefer first-frame tension that can be seen on screen, not only explained in voiceover.
""".strip()


def viral_script_prompt() -> str:
    patterns = ", ".join(VIRAL_HOOK_PATTERNS)
    return f"""
Viral scripting rules:
- Select one hook_pattern from: {patterns}.
- Hook must be under 15 words, spoken immediately, and visually verifiable.
- Start mid-action. No greetings, no setup, no "in this video", no "let's dive in".
- Write from mechanism, not topic: show how the mistake, leak, or advantage actually works.
- Include first_frame_text: max 4 words, shorter than the spoken hook.
- Include visual_proof: what the viewer sees when the mechanism is explained.
- Include visual_retention_plan: first frame, proof cutaway, pacing, and loop/callback.
- Use contrast: most sellers do the lazy/common thing; this episode shows the smarter mechanism.
- Every sentence must earn retention through tension, proof, or payoff.

Anti-slop bans:
- No three-word hype loops like "fast, easy, effective".
- No question-answer list rhythm like "Problem? Time. Solution? AI."
- No generic transitions: "here's the kicker", "game changer", "mind-blowing".
- No imaginary scenes. Use actual Amazon/ecommerce operator moments.
""".strip()

