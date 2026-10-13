"""Render an official single-page Marathi report PDF from a grounded report.

Uses fpdf2 with HarfBuzz text shaping (uharfbuzz) so Devanagari renders correctly,
Noto Serif Devanagari for Marathi, and DejaVu Serif as a Latin/digit fallback.
Grounded figures (tokens with a source) are rendered bold. Signatures: the report
submitter on the left, the sanctioning authority on the right.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

_NOTO = "/usr/share/fonts/truetype/noto"
_DEJAVU = "/usr/share/fonts/truetype/dejavu"
_SEAL = Path(__file__).resolve().parent / "assets" / "seal_maharashtra.png"


def _pdf_base() -> FPDF:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("Dev", "", f"{_NOTO}/NotoSerifDevanagari-Regular.ttf")
    pdf.add_font("Dev", "B", f"{_NOTO}/NotoSerifDevanagari-Bold.ttf")
    pdf.add_font("Lat", "", f"{_DEJAVU}/DejaVuSerif.ttf")
    pdf.add_font("Lat", "B", f"{_DEJAVU}/DejaVuSerif-Bold.ttf")
    pdf.set_text_shaping(True)          # HarfBuzz shaping for Devanagari
    pdf.set_fallback_fonts(["Lat"])     # ASCII digits / hyphens / punctuation
    return pdf


def render_report_pdf(title: str, sections: list[dict],
                      submitted_by: str = "अहवाल सादरकर्ता\n(ग्रामसेवक)",
                      authorised_by: str = "सक्षम अधिकारी\n(सरपंच)",
                      place: str = "") -> bytes:
    pdf = _pdf_base()
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(False)   # single page: signatures/footer are placed by hand
    pdf.add_page()
    W = pdf.w - pdf.l_margin - pdf.r_margin
    teal = (92, 145, 131)
    ink = (37, 31, 33)
    muted = (88, 82, 84)

    # outer official frame
    pdf.set_draw_color(*teal)
    pdf.set_line_width(0.6)
    pdf.rect(8, 8, pdf.w - 16, pdf.h - 16)
    pdf.set_line_width(0.2)
    pdf.rect(10, 10, pdf.w - 20, pdf.h - 20)

    # letterhead: Maharashtra emblem top-left + title block
    if _SEAL.exists():
        pdf.image(str(_SEAL), x=pdf.l_margin, y=13, w=18, h=18)
    hx, hw = pdf.l_margin + 22, W - 22
    pdf.set_xy(hx, 14)
    pdf.set_text_color(*muted)
    pdf.set_font("Dev", "", 11)
    pdf.cell(hw, 6, "महाराष्ट्र शासन", align="C")
    pdf.set_xy(hx, 20)
    pdf.set_font("Dev", "", 9)
    pdf.cell(hw, 5, "शासकीय अहवाल", align="C")
    pdf.set_xy(hx, 25)
    pdf.set_text_color(*ink)
    pdf.set_font("Dev", "B", 15)
    pdf.multi_cell(hw, 7, title, align="C")
    pdf.ln(1)
    y = max(pdf.get_y(), 33)
    pdf.set_draw_color(*teal)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(3)

    # date line (right)
    pdf.set_font("Dev", "", 10)
    pdf.set_text_color(*muted)
    pdf.cell(W, 6, f"दिनांक: {date.today().isoformat()}", align="R",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_text_color(*ink)

    # body
    for s in sections:
        pdf.set_font("Dev", "B", 12)
        pdf.set_text_color(*teal)
        pdf.multi_cell(W, 7, s.get("heading", ""), align="L")
        pdf.set_text_color(*ink)
        pdf.set_font("Dev", "", 12)
        pdf.set_x(pdf.l_margin)
        for tok in s.get("tokens", []):
            pdf.set_font("Dev", "B" if tok.get("source") else "", 12)
            pdf.write(7, tok.get("text", ""))
        pdf.ln(9)

    # signatures pinned near the bottom
    sig_y = pdf.h - 36
    half = (W - 10) / 2
    pdf.set_draw_color(*muted)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, sig_y, pdf.l_margin + half, sig_y)             # left line
    pdf.line(pdf.w - pdf.r_margin - half, sig_y, pdf.w - pdf.r_margin, sig_y)  # right line
    pdf.set_xy(pdf.l_margin, sig_y + 1)
    pdf.set_font("Dev", "", 10)
    pdf.set_text_color(*ink)
    pdf.multi_cell(half, 5, submitted_by, align="L")
    pdf.set_xy(pdf.w - pdf.r_margin - half, sig_y + 1)
    pdf.multi_cell(half, 5, authorised_by, align="R")

    # footer
    pdf.set_y(pdf.h - 16)
    pdf.set_font("Dev", "", 8)
    pdf.set_text_color(*muted)
    foot = "या अहवालातील प्रत्येक आकडा स्रोत नोंदीशी पडताळून तयार करण्यात आला आहे."
    if place:
        foot = f"स्थळ: {place}    " + foot
    pdf.cell(W, 5, foot, align="C")

    out = pdf.output()
    return bytes(out)
