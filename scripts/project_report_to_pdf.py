#!/usr/bin/env python3
"""Build PROJECT_REPORT.pdf from PROJECT_REPORT.md (requires: pip install fpdf2)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from fpdf import FPDF
except ImportError:
    print("Install fpdf2:  pip install fpdf2", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
MD = ROOT / "PROJECT_REPORT.md"
PDF = ROOT / "PROJECT_REPORT.pdf"


def _strip_md(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return s


def _ascii_safe(s: str) -> str:
    """Replace common Unicode so core Helvetica works."""
    reps = {
        "–": "-",
        "—": "-",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "…": "...",
        "►": ">",
        "▼": "v",
        "┌": "+",
        "┐": "+",
        "└": "+",
        "┘": "+",
        "│": "|",
        "─": "-",
    }
    for u, a in reps.items():
        s = s.replace(u, a)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def main() -> int:
    if not MD.exists():
        print(f"Missing {MD}", file=sys.stderr)
        return 1

    raw = MD.read_text(encoding="utf-8")
    pdf = FPDF()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 11)
    # Usable width between margins (avoids "not enough horizontal space" after drawings)
    epw = pdf.w - pdf.l_margin - pdf.r_margin

    def _mc(text: str, h: float, font_size: int | None = None, style: str = "") -> None:
        if font_size is not None:
            pdf.set_font("Helvetica", style, font_size)
        text = (text or " ").strip()
        if not text:
            pdf.ln(h * 0.3)
            return
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(epw, h, text)

    in_code = False
    for line in raw.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            pdf.set_font("Helvetica", "", 11)
            pdf.ln(2)
            continue
        if in_code:
            pdf.set_font("Courier", "", 8)
            chunk = _ascii_safe(line) if line.strip() else " "
            _mc(chunk, 4)
            pdf.set_font("Helvetica", "", 11)
            continue

        t = line.rstrip()
        if not t.strip():
            pdf.ln(3)
            continue
        if t.strip() == "---":
            y = pdf.get_y()
            pdf.set_draw_color(180, 180, 180)
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.set_y(y + 4)
            pdf.set_x(pdf.l_margin)
            continue

        t = _strip_md(t)
        t = _ascii_safe(t)

        if t.startswith("# "):
            _mc(t[2:].strip(), 8, 16, "B")
            pdf.ln(2)
            pdf.set_font("Helvetica", "", 11)
        elif t.startswith("## "):
            _mc(t[3:].strip(), 7, 13, "B")
            pdf.ln(1)
            pdf.set_font("Helvetica", "", 11)
        elif t.startswith("### "):
            _mc(t[4:].strip(), 6, 11, "B")
            pdf.set_font("Helvetica", "", 11)
        elif re.match(r"^\|.+\|$", t.strip()) and "---" not in t:
            pdf.set_font("Courier", "", 8)
            _mc(t.strip(), 4)
            pdf.set_font("Helvetica", "", 11)
        elif t.lstrip().startswith("- "):
            pdf.set_x(pdf.l_margin + 4)
            pdf.multi_cell(epw - 4, 5, "* " + t.lstrip()[2:].strip())
        else:
            _mc(t, 5)

    pdf.output(PDF)
    print(f"Wrote {PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
