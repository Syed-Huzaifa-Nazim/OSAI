"""Chunking (stage 3).

Overlap matters: a claim that straddles a chunk boundary has to stay
retrievable, because every gap the Insight Agent reports must cite a passage.
"""

from __future__ import annotations

from app.api.v1.agents.preprocess import chunk_text


def test_short_text_is_one_chunk() -> None:
    assert chunk_text("A short line.") == ["A short line."]


def test_empty_text_produces_nothing() -> None:
    assert chunk_text("") == []


def test_long_text_is_split() -> None:
    text = " ".join(f"Sentence number {index}." for index in range(1, 200))
    chunks = chunk_text(text, size=200, overlap=40)

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)


def test_chunking_terminates_on_pathological_input() -> None:
    """A window that cannot advance would loop forever; guard against it."""
    chunks = chunk_text("x" * 5000, size=100, overlap=99)
    assert len(chunks) < 500
    assert "".join(chunks)


def test_chunks_overlap() -> None:
    text = " ".join(f"word{index}" for index in range(1, 400))
    chunks = chunk_text(text, size=300, overlap=80)

    assert len(chunks) >= 2
    # The tail of one chunk should reappear at the head of the next.
    first_tail = chunks[0][-40:]
    assert any(fragment in chunks[1] for fragment in first_tail.split()[:3])
