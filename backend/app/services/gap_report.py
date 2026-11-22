"""The gap report as a PDF: every gap (or only the kept ones), its numbers, example posts with pictures, and the
explanation the seller generated with the Explain button (saved on the gap as details.explanation).

Pictures are fetched from Instagram's CDN with the media proxy's own safe fetcher, shrunk, and embedded. Instagram's
links expire after a few days, so an old project prints "no picture" for those posts rather than failing.
"""
from __future__ import annotations

import io
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from app.services.post_stills import post_stills

logger = logging.getLogger("optistratix.gap_report")

LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo-wide.png"
VIOLET = "#5B3BE6"
THUMB_PX = 220                  # longest side of an embedded picture, in pixels
MAX_PICTURE_BYTES = 8_000_000
FETCH_WORKERS = 6
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
KIND_LABEL = {"format": "Types of post", "timing": "When they post", "reach": "Reel reach", "topic": "Topics", "hashtag": "Hashtags", "media": "Pictures and videos",
              "weakness": "Your weak spot", "habit": "Habits", "profile": "Profile"}
# PDF fonts cannot draw emoji; they are removed rather than printed as empty boxes
_EMOJI = re.compile("[\U00010000-\U0010FFFF☀-➿️‍]")


def _clean(text: Any) -> str:
    return escape(_EMOJI.sub("", str(text or "")).strip())


def _uncite_k(text: Any) -> str:
    return re.sub(r"\s*\[K\d+\](\s*,\s*\[K\d+\])*", "", str(text or ""))


def _uncite(text: Any) -> str:
    """Explanations cite posts as [E1]; in print the posts are listed under the gap instead."""
    return re.sub(r"\s*\[E\d+\](\s*,\s*\[E\d+\])*", "", str(text or ""))


def _fonts() -> tuple[str, str]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular, bold = FONT_DIR / "DejaVuSans.ttf", FONT_DIR / "DejaVuSans-Bold.ttf"
    if regular.exists() and bold.exists():
        if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("DejaVu", str(regular)))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(bold)))
        return "DejaVu", "DejaVu-Bold"
    return "Helvetica", "Helvetica-Bold"


def _picture(url: str) -> bytes | None:
    """A small JPEG of the picture at `url`, or None (expired link, a video file, not an image...)."""
    if not url:
        return None
    try:
        from PIL import Image

        from app.scrapers.instagram import media as instagram_media

        _, content_type, _, chunks = instagram_media.open_stream(url)
        if not content_type.startswith("image/"):
            return None
        buf, size = io.BytesIO(), 0
        for chunk in chunks:
            size += len(chunk)
            if size > MAX_PICTURE_BYTES:
                return None
            buf.write(chunk)
        img = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
        img.thumbnail((THUMB_PX, THUMB_PX))
        out = io.BytesIO()
        img.save(out, "JPEG", quality=80)
        return out.getvalue()
    except Exception as exc:  # noqa: BLE001 - one dead link must not stop the report
        logger.info("No picture for the report from %s: %s", url[:80], exc)
        return None


def select_gaps(gaps: list[dict[str, Any]], which: str) -> list[dict[str, Any]]:
    keep = [g for g in gaps if which != "kept" or g.get("decision") == "accepted"]
    sure = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(keep, key=lambda g: (bool((g.get("details") or {}).get("unproven")),
                                       sure.get((g.get("details") or {}).get("howSure"), 3)))


def render_gaps_pdf(repo, project: dict[str, Any], gaps: list[dict[str, Any]], which: str = "all") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    regular, bold = _fonts()
    st = {
        "h1": ParagraphStyle("h1", fontName=bold, fontSize=17, leading=21, spaceAfter=4),
        "meta": ParagraphStyle("meta", fontName=regular, fontSize=9, leading=12, textColor=colors.HexColor("#555555")),
        "h2": ParagraphStyle("h2", fontName=bold, fontSize=12.5, leading=16, spaceBefore=6, spaceAfter=3),
        "label": ParagraphStyle("label", fontName=bold, fontSize=8.5, leading=11, textColor=colors.HexColor("#666666"),
                                spaceBefore=4),
        "body": ParagraphStyle("body", fontName=regular, fontSize=9.5, leading=13),
        "small": ParagraphStyle("small", fontName=regular, fontSize=8, leading=10.5),
        "tag": ParagraphStyle("tag", fontName=bold, fontSize=8.5, leading=11, textColor=colors.HexColor(VIOLET)),
    }
    chosen = select_gaps(gaps, which)

    # pictures, fetched in parallel
    covers = post_stills(repo, project["id"])
    wanted: dict[str, str] = {}
    for g in chosen:
        for ex in (g.get("details") or {}).get("examples") or []:
            url = ex.get("postUrl") or ""
            still = covers.get(url) or ("" if str(ex.get("format", "")).startswith("video") else ex.get("imageUrl") or "")
            if url and still:
                wanted[url] = still
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        pictures = dict(zip(wanted, pool.map(_picture, wanted.values())))

    story: list[Any] = []
    title = project.get("name") or "Instagram gap report"
    story.append(Paragraph(_clean(f"Gap report: {title}"), st["h1"]))
    story.append(Paragraph(_clean(
        f"{'Gaps you kept' if which == 'kept' else 'All gaps found'}: {len(chosen)} · "
        f"made {datetime.now(timezone.utc).strftime('%d %b %Y')}"), st["meta"]))
    story.append(Paragraph(
        "Each gap compares your Instagram with your competitor's, using your real posts. \"Not proven yet\" means a "
        "real difference that could still be chance with this many posts: something to test.", st["meta"]))
    story.append(Spacer(1, 6 * mm))
    if not chosen:
        story.append(Paragraph("No gaps to show." if which == "all" else
                               "No gaps have been kept yet. Keep gaps on the Review gaps page first.", st["body"]))

    for n, g in enumerate(chosen, 1):
        d = g.get("details") or {}
        tag = "Not proven yet: worth testing" if d.get("unproven") else f"How sure: {d.get('howSure') or 'not stated'}"
        if g.get("decision") == "accepted":
            tag += " · kept"
        block: list[Any] = [
            Paragraph(_clean(f"{n}. {g.get('title')}"), st["h2"]),
            Paragraph(_clean(f"{KIND_LABEL.get(d.get('kind'), 'Gap')} · {tag}"), st["tag"]),
            Paragraph("What we saw", st["label"]), Paragraph(_clean(g.get("description")), st["body"]),
        ]

        rows = d.get("numbers") or []
        if rows:
            data = [[Paragraph("<b>What</b>", st["small"]), Paragraph("<b>You</b>", st["small"]),
                     Paragraph("<b>Competitor</b>", st["small"]), Paragraph("<b>Typical</b>", st["small"])]]
            data += [[Paragraph(_clean(r.get("label")), st["small"]), Paragraph(_clean(r.get("you") or "-"), st["small"]),
                      Paragraph(_clean(r.get("competitor") or "-"), st["small"]),
                      Paragraph(_clean(r.get("typical") or "-"), st["small"])] for r in rows]
            t = Table(data, colWidths=[52 * mm, 40 * mm, 40 * mm, 38 * mm])
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                                   ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            block += [Spacer(1, 2 * mm), t]

        exp = d.get("explanation") or {}
        if exp.get("found") or exp.get("why") or exp.get("explanation"):
            block.append(Paragraph("In simple words (from the Explain button)", st["label"]))
            if exp.get("found") or exp.get("why"):
                if exp.get("found"):
                    block.append(Paragraph(_clean(f"What the numbers show: {_uncite(exp['found'])}"), st["body"]))
                if exp.get("why"):
                    block.append(Paragraph(_clean(f"Why this is a gap: {_uncite(exp['why'])}"), st["body"]))
                if exp.get("general"):
                    used = [k for k in exp.get("knowledge") or [] if k.get("id") in (exp.get("knowledge_used") or [])]
                    src = "; ".join(_clean(k.get("source")) for k in used)
                    block.append(Paragraph(_clean(f"Why this can matter: {_uncite_k(exp['general'])}")
                                           + (f" <font size=7 color='#777777'>(Source: {src})</font>" if src else ""),
                                           st["body"]))
            else:
                block.append(Paragraph(_clean(_uncite(exp.get("explanation"))), st["body"]))
            if not exp.get("grounded"):
                block.append(Paragraph("Treat with care: this explanation did not point to the posts it was given.",
                                       st["small"]))
        story.append(KeepTogether(block))

        examples = d.get("examples") or []
        if examples:
            story.append(Paragraph("Example posts", st["label"]))
            cells = []
            for ex in examples:
                pic = pictures.get(ex.get("postUrl") or "")
                img = Image(io.BytesIO(pic), width=24 * mm, height=24 * mm, kind="proportional") if pic else \
                    Paragraph("no picture", st["small"])
                likes = "hidden" if ex.get("likes") is None else f"{ex['likes']:,}"
                comments = "-" if ex.get("comments") is None else f"{ex['comments']:,}"
                caption = _clean((ex.get("caption") or "")[:140])
                link = f'<link href="{escape(ex["postUrl"])}" color="blue">open</link>' if ex.get("postUrl") else ""
                text = Paragraph(
                    f"<b>{'You' if ex.get('who') == 'you' else 'Competitor'}</b> · {_clean(ex.get('format'))}"
                    f"{' · ' + _clean(ex.get('date')) if ex.get('date') else ''}<br/>"
                    f"{likes} likes · {comments} comments {link}<br/>{caption}", st["small"])
                cell = Table([[img], [text]], colWidths=[54 * mm])
                cell.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                          ("ALIGN", (0, 0), (0, 0), "LEFT")]))
                cells.append(cell)
            grid = [cells[i:i + 3] + [""] * (3 - len(cells[i:i + 3])) for i in range(0, len(cells), 3)]
            t = Table(grid, colWidths=[57 * mm] * 3)
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            story.append(t)
        story.append(Spacer(1, 7 * mm))

    buf = io.BytesIO()
    page_decor = _page_decor(regular, bold, title)
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=28 * mm, bottomMargin=20 * mm,
                      title=f"Gap report: {title}", author="OptiStratixAI").build(
        story, onFirstPage=page_decor, onLaterPages=page_decor)
    return buf.getvalue()


def _page_decor(regular: str, bold: str, project: str):
    """Every page: the logo and name at the top, a faint diagonal watermark, and a footer with the page number."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    width, height = A4

    def draw(canvas, doc) -> None:
        canvas.saveState()
        # watermark
        canvas.setFillColor(colors.HexColor(VIOLET))
        canvas.setFillAlpha(0.045)
        canvas.setFont(bold, 64)
        canvas.translate(width / 2, height / 2)
        canvas.rotate(35)
        canvas.drawCentredString(0, 0, "OptiStratixAI")
        canvas.restoreState()

        canvas.saveState()
        # header: logo + name on the left, the project on the right, a thin violet line under them
        top = height - 12 * mm
        x = 18 * mm
        if LOGO.exists():
            canvas.drawImage(str(LOGO), x, top - 8.5 * mm, width=11 * mm, height=8.5 * mm, mask="auto",
                             preserveAspectRatio=True)
            x += 13 * mm
        canvas.setFillColor(colors.HexColor("#13112B"))
        canvas.setFont(bold, 12)
        canvas.drawString(x, top - 5.6 * mm, "OptiStratixAI")
        canvas.setFont(regular, 8)
        canvas.setFillColor(colors.HexColor("#5B5878"))
        canvas.drawRightString(width - 18 * mm, top - 5.6 * mm, _plain(f"Competitor gap report · {project}")[:80])
        canvas.setStrokeColor(colors.HexColor(VIOLET))
        canvas.setLineWidth(1.2)
        canvas.line(18 * mm, top - 11 * mm, width - 18 * mm, top - 11 * mm)
        # footer
        canvas.setStrokeColor(colors.HexColor("#DDD6FE"))
        canvas.setLineWidth(0.6)
        canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
        canvas.setFont(regular, 7.5)
        canvas.setFillColor(colors.HexColor("#5B5878"))
        canvas.drawString(18 * mm, 9.5 * mm, "OptiStratixAI · Competitor analysis for small online sellers")
        canvas.drawRightString(width - 18 * mm, 9.5 * mm, f"Page {doc.page}")
        canvas.restoreState()

    return draw


def _plain(text: str) -> str:
    """Text for drawing straight onto the page (no markup, no emoji)."""
    return _EMOJI.sub("", str(text or "")).strip()


__all__ = ["render_gaps_pdf", "select_gaps"]
