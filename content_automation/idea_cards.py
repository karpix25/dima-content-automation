from __future__ import annotations

from .idea_bank import ContentIdea


def select_visible_idea(ideas: list[ContentIdea], *, after_id: int | None = None) -> ContentIdea | None:
    if not ideas:
        return None
    if after_id is None:
        return ideas[0]
    return next((item for item in ideas if item.id < after_id), ideas[0])


def format_idea_card(idea: ContentIdea, *, index: int | None = None, total: int | None = None) -> str:
    prefix = f"Reddit-тема {index}/{total}" if index and total else f"Reddit-тема #{idea.id}"
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
