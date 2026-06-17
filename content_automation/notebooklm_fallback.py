from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotebookLMFallbackClient:
    primary: Any
    fallback: Any
    fallback_label: str = "NotebookLM MCP"
    before_fallback: Callable[[], None] | None = None

    def ask(self, question: str, *, notebook_url: str | None = None, notebook_id: str | None = None):
        try:
            return self.primary.ask(question, notebook_url=notebook_url, notebook_id=notebook_id)
        except Exception as exc:
            logger.warning("%s failed; falling back to %s: %s", self.primary.__class__.__name__, self.fallback_label, exc)
            if self.before_fallback:
                self.before_fallback()
            return self.fallback.ask(question, notebook_url=notebook_url, notebook_id=notebook_id)
