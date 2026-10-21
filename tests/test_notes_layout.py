"""Notes from a chat read like revision notes, not a transcript, and render cleanly as PDF."""

from types import SimpleNamespace

from app.services.notes import _deterministic_draft, _markdown_note, build_note_pdf


def test_offline_notes_are_sections_not_a_transcript() -> None:
    material = "Learner: What is a primary key?\n\nARIA: A primary key uniquely identifies each row."
    draft = _deterministic_draft(material, "Databases")
    assert "## Primary Key" in draft.body
    assert "uniquely identifies each row" in draft.body
    assert "Learner:" not in draft.body and "ARIA:" not in draft.body


def test_markdown_notes_take_their_title_from_the_first_heading() -> None:
    draft = _markdown_note("# Primary keys\n\n## Definition\nA **primary key** is unique.", "fallback")
    assert draft.title == "Primary keys"
    assert draft.body.startswith("## Definition")


def test_pdf_renders_headings_bullets_and_code() -> None:
    body = "## Keys\n\nA **primary key** is unique.\n\n- one\n- two\n\n```sql\nSELECT 1;\n```\n\n## Summary\n- done"
    note = SimpleNamespace(title="Keys", body=body, source_refs=[])
    pdf = build_note_pdf(note)
    assert pdf.startswith(b"%PDF") and len(pdf) > 1000


def test_pdf_text_maps_symbols_the_standard_font_cannot_draw() -> None:
    from app.services.notes import pdf_safe

    text = "prompt\u2011response \u2192 goal \u2264 3 \u2014 caf\u00e9"
    assert pdf_safe(text) == "prompt-response -> goal <= 3 \u2014 caf\u00e9"  # em dash and accents survive
    pdf_safe(text).encode("cp1252")  # everything left is drawable by Helvetica
