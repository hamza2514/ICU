"""Date-range helpers: nice labels ("1st – 10th October 2026") and a
best-effort parser that turns such labels (or OCR/Excel text) back into dates."""
from __future__ import annotations

import calendar
import re
from datetime import date

_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
_MONTHS["sept"] = 9


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def format_range(a: date, b: date, short: bool = False) -> str:
    """short -> '1st Oct – 10th Oct' (table rows); long -> '1st – 10th October 2026'."""
    if a > b:
        a, b = b, a
    if short:
        return f"{ordinal(a.day)} {a.strftime('%b')} – {ordinal(b.day)} {b.strftime('%b')}"
    if a == b:
        return f"{ordinal(a.day)} {a.strftime('%B %Y')}"
    if (a.year, a.month) == (b.year, b.month):
        return f"{ordinal(a.day)} – {ordinal(b.day)} {b.strftime('%B %Y')}"
    if a.year == b.year:
        return f"{ordinal(a.day)} {a.strftime('%B')} – {ordinal(b.day)} {b.strftime('%B %Y')}"
    return f"{ordinal(a.day)} {a.strftime('%B %Y')} – {ordinal(b.day)} {b.strftime('%B %Y')}"


_TOK = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s*([A-Za-z]{3,9})?", re.I)


def parse_range(text: str, default_year: int, default_month: int | None = None):
    """Best effort: '1st Oct-10th oct', '1 Aug - 7 Aug', '11th – 27th July 2026'
    -> (date, date). Returns None if it can't be understood."""
    if not text:
        return None
    t = re.sub(r"[–—]", "-", text)
    ym = re.search(r"\b(20\d{2})\b", t)
    year = int(ym.group(1)) if ym else default_year
    t = re.sub(r"\b20\d{2}\b", "", t)
    parts = [p for p in re.split(r"\s*-\s*|\s+to\s+", t.strip(), maxsplit=1) if p.strip()]
    if len(parts) == 1:
        parts = parts * 2
    if len(parts) != 2:
        return None
    toks = []
    for p in parts:
        m = _TOK.search(p)
        if not m:
            return None
        day = int(m.group(1))
        mon = _MONTHS.get((m.group(2) or "").lower())
        toks.append([day, mon])
    if toks[0][1] is None:
        toks[0][1] = toks[1][1] or default_month
    if toks[1][1] is None:
        toks[1][1] = toks[0][1]
    try:
        a = date(year, toks[0][1], toks[0][0])
        b = date(year, toks[1][1], toks[1][0])
    except (TypeError, ValueError):
        return None
    return (a, b) if a <= b else (b, a)
