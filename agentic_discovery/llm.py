"""Thin Claude client used by ClaudeBrain.

Kept deliberately small: a JSON call (structured extraction/ranking) and a text
call (question phrasing). The anthropic SDK is imported lazily so the package —
and the offline MockBrain demo and tests — work without it installed.
"""

from __future__ import annotations

import json

MODEL = "claude-opus-4-8"


class ClaudeLLM:
    def __init__(self, model: str = MODEL) -> None:
        try:
            import anthropic  # noqa: F401
        except ImportError as e:  # pragma: no cover - exercised only with --claude
            raise RuntimeError(
                "The Claude brain needs the anthropic SDK: pip install 'agentic-discovery[claude]'"
            ) from e
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.model = model

    def text(self, system: str, prompt: str, max_tokens: int = 2000) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    def json(self, system: str, prompt: str, schema: dict,
             max_tokens: int = 4000) -> dict:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            output_config={"effort": "high",
                           "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}],
        )
        text = next(b.text for b in resp.content if b.type == "text")
        return json.loads(text)
