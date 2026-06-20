"""Interaction channels — how the agent talks to a human.

The engine only ever calls `ask()` / `say()`, so the medium is swappable:
text now, voice next, an avatar later. Each new surface is a new channel, not
a change to the engine. This is the seam the voice/avatar roadmap plugs into.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class InteractionChannel(ABC):
    @abstractmethod
    def ask(self, question: str) -> str:
        """Put a question to the person and return their answer."""

    def say(self, message: str) -> None:
        """Out-of-band narration (progress, transitions). Optional."""


class TextChannel(InteractionChannel):
    """Turn-based terminal chat — the simplest form of real adaptivity."""

    def ask(self, question: str) -> str:
        print(f"\n\033[1m🧭 {question}\033[0m")
        try:
            return input("   you › ").strip()
        except EOFError:
            return ""

    def say(self, message: str) -> None:
        print(f"\033[2m   · {message}\033[0m")


class ScriptedChannel(InteractionChannel):
    """Replays canned answers — drives the offline demo and tests."""

    def __init__(self, answers: list[str], echo: bool = True) -> None:
        self._answers = list(answers)
        self._echo = echo

    def ask(self, question: str) -> str:
        answer = self._answers.pop(0) if self._answers else ""
        if self._echo:
            print(f"\n\033[1m🧭 {question}\033[0m\n   you › {answer}")
        return answer


class VoiceChannel(InteractionChannel):
    """Voice surface scaffold — STT in, TTS out. Not wired in this build.

    Two integration paths, both designed to fit behind this same interface:

    1. Browser (recommended first voice step): a thin web UI uses the Web Speech
       API — `SpeechRecognition` for speech-to-text and `SpeechSynthesis` for
       text-to-speech — talking to the engine over a small websocket/HTTP API.
       Zero vendor keys, lowest-friction path to the voice experience, and the
       natural home for an avatar later.
    2. Server-side: plug a transcription backend into `transcribe()` and a TTS
       backend into `synthesize()` (e.g. a cloud STT/TTS service, or local
       libraries). The engine code does not change either way.
    """

    def transcribe(self, audio: bytes) -> str:  # pragma: no cover - scaffold
        raise NotImplementedError("wire a speech-to-text backend here")

    def synthesize(self, text: str) -> bytes:  # pragma: no cover - scaffold
        raise NotImplementedError("wire a text-to-speech backend here")

    def ask(self, question: str) -> str:  # pragma: no cover - scaffold
        raise NotImplementedError(
            "VoiceChannel is a scaffold — see module docstring for the two "
            "integration paths (browser Web Speech API or server-side STT/TTS).")
