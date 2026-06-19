from __future__ import annotations

from .idea_bank import ContentIdea


def select_visible_idea(ideas: list[ContentIdea], *, after_id: int | None = None) -> ContentIdea | None:
    if not ideas:
        return None
    if after_id is None:
        return ideas[0]
    return next((item for item in ideas if item.id < after_id), ideas[0])


def format_idea_card(idea: ContentIdea, *, index: int | None = None, total: int | None = None) -> str:
    source = source_label(idea.source)
    prefix = f"{source}-тема {index}/{total}" if index and total else f"{source}-тема #{idea.id}"
    meta = idea.source_meta
    stats = []
    if meta.get("comments") is not None:
        stats.append(f"{meta.get('comments')} comments")
    if meta.get("score") is not None:
        stats.append(f"{meta.get('score')} upvotes")
    stats_text = ", ".join(stats)
    return "\n\n".join(
        [
            prefix,
            f"Тема:\n{idea.title}",
            f"Боль:\n{idea.pain}",
            f"Угол:\n{idea.angle}",
            f"Сигнал:\n{idea.summary}",
            f"Метрики: {stats_text}" if stats_text else "",
            f"Источник:\n{idea.source_url}",
        ]
    ).replace("\n\n\n", "\n\n").strip()


def idea_to_topic_hint(idea: ContentIdea) -> str:
    if idea.source == "notebooklm_plan":
        meta = idea.source_meta
        return "\n".join(
            [
                "Use this NotebookLM producer-plan episode seed.",
                f"Episode day: {meta.get('day') or ''}",
                f"Content pillar: {meta.get('pillar') or ''}",
                f"Preferred format: {meta.get('format') or ''}",
                f"Topic title: {idea.title}",
                f"Observed pain: {idea.pain}",
                f"Content angle: {idea.angle}",
                f"Viral angle: {meta.get('viral_angle') or ''}",
                f"Hook pattern: {meta.get('hook_pattern') or ''}",
                f"Mechanism to explain: {meta.get('mechanism') or ''}",
                f"First-frame text: {meta.get('first_frame_text') or ''}",
                f"Producer summary: {idea.summary}",
                f"Visual direction: {meta.get('visual_note') or ''}",
                f"Visual proof: {meta.get('visual_proof') or ''}",
                f"Source basis: {meta.get('source_basis') or ''}",
                "Develop the script through the author's NotebookLM knowledge base. Do not invent external claims.",
            ]
        )
    if idea.source == "notebooklm":
        meta = idea.source_meta
        return "\n".join(
            [
                "Use this NotebookLM-derived topic seed.",
                f"Topic title: {idea.title}",
                f"Observed pain: {idea.pain}",
                f"Content angle: {idea.angle}",
                f"Viral angle: {meta.get('viral_angle') or ''}",
                f"Hook pattern: {meta.get('hook_pattern') or ''}",
                f"Mechanism to explain: {meta.get('mechanism') or ''}",
                f"First-frame text: {meta.get('first_frame_text') or ''}",
                f"Visual proof: {meta.get('visual_proof') or ''}",
                f"Source context: {idea.summary}",
                "Develop the script through the author's NotebookLM knowledge base. Do not invent external claims.",
            ]
        )
    return "\n".join(
        [
            "Use this current Reddit market signal as the topic seed.",
            f"Reddit title: {idea.title}",
            f"Observed pain: {idea.pain}",
            f"Content angle: {idea.angle}",
            f"Source context: {idea.summary}",
            f"Source URL: {idea.source_url}",
            "Do not quote Reddit directly. Explain this market pain through the author's NotebookLM knowledge base.",
        ]
    )


def source_label(source: str) -> str:
    if source == "notebooklm_plan":
        return "NotebookLM план"
    if source == "notebooklm":
        return "NotebookLM"
    if source == "reddit":
        return "Reddit"
    return source
