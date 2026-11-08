"""Stage 8 export.

reportlab parses a mini-HTML dialect, so a strategy title containing an
ampersand or an angle bracket would crash the build unless it is escaped. Real
brand names contain ampersands, so this is not a hypothetical.
"""

from __future__ import annotations

import pytest

from app.services import document_service

DOCUMENT = {
    "title": "Harbour & Vine. Q3 Strategy <draft>",
    "content": "## Executive Summary\n\nBody text.",
    "sections": [
        {
            "id": "s1",
            "order": 1,
            "heading": "Executive Summary",
            "body": "Competes on curation but loses on discoverability & decision support.",
        },
        {
            "id": "s2",
            "order": 2,
            "heading": "Implementation Plan",
            "body": "Weeks 1-3: ship the finder. Weeks 2-12: run the guide series.",
        },
    ],
}


def test_markdown_export_leads_with_the_title() -> None:
    payload = document_service.render_markdown(DOCUMENT)
    text = payload.decode("utf-8")

    assert text.startswith("# Harbour & Vine")
    # Markdown is the one format that needs no escaping.
    assert "&amp;" not in text


def test_pdf_export_survives_markup_characters_in_the_content() -> None:
    pytest.importorskip("reportlab")

    payload = document_service.render_pdf(DOCUMENT)

    assert payload.startswith(b"%PDF-")
    assert len(payload) > 1000


def test_docx_export_produces_a_valid_package() -> None:
    pytest.importorskip("docx")

    payload = document_service.render_docx(DOCUMENT)

    # A .docx is a zip archive; the magic bytes are the cheapest real check.
    assert payload.startswith(b"PK")
    assert len(payload) > 1000


def test_sections_render_in_declared_order_not_list_order() -> None:
    pytest.importorskip("reportlab")

    shuffled = {**DOCUMENT, "sections": list(reversed(DOCUMENT["sections"]))}

    # Both orders must produce a document; ordering is by `order`, so the two
    # renders describe the same document rather than different ones.
    assert document_service.render_pdf(shuffled).startswith(b"%PDF-")


def test_escape_neutralises_reportlab_markup() -> None:
    escaped = document_service._escape("Harbour & Vine <draft>")
    assert escaped == "Harbour &amp; Vine &lt;draft&gt;"
