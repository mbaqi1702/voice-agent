"""
Document dictation helpers.
Splits long documents into speakable chunks.
"""

from __future__ import annotations

from typing import Generator


def split_for_dictation(text: str, max_chars: int = 400) -> Generator[str, None, None]:
    """
    Yield reasonably sized chunks for TTS.
    Tries to break on sentence boundaries.
    """
    import re

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip()
        else:
            if current:
                yield current
            current = sentence

    if current:
        yield current


def prepare_dictation(text: str, section: str | None = None) -> list[str]:
    """
    Prepare a list of speakable chunks.
    If section is provided, try a simple keyword filter (MVP).
    """
    if section and section.lower() != "full":
        # Very simple section filter for MVP
        lines = text.splitlines()
        filtered = []
        capture = False
        for line in lines:
            if section.lower() in line.lower():
                capture = True
            if capture:
                filtered.append(line)
        text = "\n".join(filtered) if filtered else text

    return list(split_for_dictation(text))
