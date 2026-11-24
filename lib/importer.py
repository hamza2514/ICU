"""Reads the unit's weekly/monthly summary tables from an Excel file or a
screenshot and turns them into the raw numbers the dashboards need.

Both inputs are reduced to the same thing - rows of (x_position, text) cells -
and then one parser finds every block that has the four headers
"Rejections In / Rejections Out / Alteration In / Alteration Out", and reads
Units + Production underneath. Percentages are NOT trusted from the file;
they are recalculated by the app. The file's own "Net Confirmed Rejection"
value is only read so the app can cross-check the numbers it extracted
(this catches OCR misreads).

Public API:
    parse_excel(file_bytes) -> list[Block]
    parse_image(file_bytes) -> list[Block]
    split_total(blocks)     -> (week_blocks, total_block_or_None)
"""
from __future__ import annotations

import io
import re

KEYS = ("rej_in", "rej_out", "alt_in", "alt_out")

_SINGLE_HDR = re.compile(r"^(rejections?|alterations?)\s*(in|out|ln|1n)$", re.I)
_FIRST_HDR = re.compile(r"^(rejections?|alterations?)$", re.I)
_SECOND_HDR = re.compile(r"^(in|out|ln|1n)$", re.I)
_INT = re.compile(r"^\d{1,3}(,\d{3})*$|^\d+$")
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_LABEL_NOISE = re.compile(
    r"units?|production|percentage|net|confirmed|rejections?|alterations?|"
    r"in process|^in$|^out$", re.I)


class ImportError_(Exception):
    pass


# --------------------------------------------------------------- parsing ----
def _hdr_key(text_a: str, text_b: str | None = None):
    """Return the KEYS entry if the text (or text pair) is one of the 4 headers."""
    a = text_a.strip()
    if text_b is None:
        m = _SINGLE_HDR.match(a)
        if not m:
            return None
        kind, direction = m.group(1).lower(), m.group(2).lower()
    else:
        if not (_FIRST_HDR.match(a) and _SECOND_HDR.match(text_b.strip())):
            return None
        kind, direction = a.lower(), text_b.strip().lower()
    prefix = "rej" if kind.startswith("rej") else "alt"
    suffix = "out" if direction == "out" else "in"
    return f"{prefix}_{suffix}"


def _find_headers(row: list[tuple[float, str]]) -> dict | None:
    found: dict[str, float] = {}
    items = sorted(row, key=lambda t: t[0])
    i = 0
    while i < len(items):
        x, t = items[i]
        key = _hdr_key(t)
        if key:
            found[key] = x
            i += 1
            continue
        if i + 1 < len(items):
            key = _hdr_key(t, items[i + 1][1])
            if key:
                found[key] = (x + items[i + 1][0]) / 2
                i += 2
                continue
        i += 1
    return found if len(found) == 4 else None


def _as_int(text: str):
    t = text.strip().replace(" ", "")
    if _INT.match(t):
        return int(t.replace(",", ""))
    return None


def _tidy_label(text: str) -> str:
    t = re.sub(r"\s+", " ", text).strip(" -|_")
    t = re.sub(r"\bist\b", "1st", t, flags=re.I)
    m = re.match(r"^(\d+\w*\s+[A-Za-z]+)\s+(\d+\w*\s+[A-Za-z]+)$", t)   # "1 Aug 7 Aug" -> "1 Aug - 7 Aug"
    return f"{m.group(1)} - {m.group(2)}" if m else t


def _parse_rows(rows: list[list[tuple[float, str]]]) -> list[dict]:
    header_rows = [(i, h) for i, r in enumerate(rows) if (h := _find_headers(r))]
    blocks = []
    for n, (hi, cols) in enumerate(header_rows):
        end = header_rows[n + 1][0] if n + 1 < len(header_rows) else len(rows)
        xs = sorted(cols.values())
        gap = min(b - a for a, b in zip(xs, xs[1:])) if len(xs) > 1 else 1
        tol = gap * 0.6

        numeric_rows = []
        for r in rows[hi + 1:end]:
            vals = {}
            for key, cx in cols.items():
                best = None
                for x, t in r:
                    v = _as_int(t)
                    if v is not None and abs(x - cx) <= tol:
                        if best is None or abs(x - cx) < abs(best[0] - cx):
                            best = (x, v)
                if best:
                    vals[key] = best[1]
            if len(vals) == 4:
                numeric_rows.append(vals)
        if len(numeric_rows) < 2:
            continue  # not a complete block (needs units + production)

        units = numeric_rows[0]
        production = next(
            (nr for nr in numeric_rows[1:] if len(set(nr.values())) == 1),
            numeric_rows[1],
        )["rej_in"]

        # label (date range) = non-keyword text left of the first header column
        left_limit = min(xs) - tol * 0.5
        parts = []
        for r in rows[hi:end]:
            for x, t in sorted(r, key=lambda c: c[0]):
                t = t.strip()
                if x < left_limit and t and not _LABEL_NOISE.search(t) and re.search(r"[A-Za-z0-9]", t):
                    parts.append(t)
        label = _tidy_label(" ".join(parts))

        # the sheet's own confirmed-rejection figure (for cross-checking only)
        confirmed_src = None
        for r in rows[hi + 1:end]:
            if any(re.search(r"confirm|net", t, re.I) for _, t in r):
                for _, t in sorted(r, key=lambda c: c[0]):
                    m = _PCT.search(t)
                    if m:
                        confirmed_src = float(m.group(1))
                        break
            if confirmed_src is not None:
                break

        blocks.append({
            "label": label, "production": production,
            "rej_in": units["rej_in"], "rej_out": units["rej_out"],
            "alt_in": units["alt_in"], "alt_out": units["alt_out"],
            "confirmed_src": confirmed_src,
        })
    return blocks


# ----------------------------------------------------------------- excel ----
def parse_excel(file_bytes: bytes) -> list[dict]:
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    for ws in wb.worksheets:
        rows = []
        for row in ws.iter_rows():
            items = []
            for c in row:
                v = c.value
                if v is None or (isinstance(v, str) and not v.strip()):
                    continue
                if isinstance(v, bool):
                    continue
                if isinstance(v, (int, float)):
                    if float(v).is_integer():
                        text = str(int(v))
                    elif abs(v) <= 1.5:          # a percentage stored as a fraction
                        text = f"{v * 100:.2f}%"
                    else:
                        text = f"{v:.2f}"
                else:
                    text = str(v)
                items.append((float(c.column), text))
            if items:
                rows.append(items)
        blocks = _parse_rows(rows)
        if blocks:
            return blocks
    return []


# ----------------------------------------------------------------- image ----
def _strip_gridlines(gray):
    """Whiten long straight dark runs (table borders) so they don't turn into
    '|' characters or glue cells together. Text strokes are far shorter."""
    import numpy as np
    a = np.array(gray)
    dark = a < 130
    h, w = dark.shape
    sc = max(1.0, w / 710.0)
    min_h, min_v = int(30 * sc), int(20 * sc)
    mask = np.zeros_like(dark)

    def runs(line, minlen):
        d = np.diff(np.concatenate(([0], line.astype(np.int8), [0])))
        for st, en in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            if en - st >= minlen:
                yield st, en

    for y in range(h):
        for st, en in runs(dark[y], min_h):
            mask[y, st:en] = True
    for x in range(w):
        for st, en in runs(dark[:, x], min_v):
            mask[st:en, x] = True
    grown = mask.copy()
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        grown |= np.roll(mask, (dy, dx), axis=(0, 1))
    a[grown] = 255
    from PIL import Image
    return Image.fromarray(a)


def _ocr_rows(file_bytes: bytes, psm: int = 6, thr: int = 150) -> list[list[tuple[float, str]]]:
    import pytesseract
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(file_bytes)).convert("L")
    img = _strip_gridlines(img)
    scale = max(1.0, 2400 / img.width)
    if scale > 1:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    img = ImageOps.autocontrast(img)
    img = img.point(lambda v: 0 if v < thr else 255)   # pure black text on white
    img = ImageOps.expand(img, border=30, fill=255)

    data = pytesseract.image_to_data(img, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    words = []
    for i, t in enumerate(data["text"]):
        t = t.strip()
        if not t or float(data["conf"][i]) < 0:
            continue
        words.append({
            "t": t,
            "x": data["left"][i] + data["width"][i] / 2,
            "y": data["top"][i] + data["height"][i] / 2,
            "h": data["height"][i],
        })
    if not words:
        return []
    words.sort(key=lambda w: w["y"])
    med_h = sorted(w["h"] for w in words)[len(words) // 2]
    rows, current = [], [words[0]]
    for w in words[1:]:
        mean_y = sum(c["y"] for c in current) / len(current)
        if w["y"] - mean_y > med_h * 0.6:
            rows.append(current)
            current = [w]
        else:
            current.append(w)
    rows.append(current)
    return [[(w["x"], w["t"]) for w in r] for r in rows]


def parse_image(file_bytes: bytes) -> list[dict]:
    best = []
    for psm in (6, 11, 4):
        blocks = _parse_rows(_ocr_rows(file_bytes, psm))
        if len(blocks) > len(best):
            best = blocks
        if best and all(b["confirmed_src"] is not None and not check_block(b) for b in best):
            break
    if not best:
        return best

    # Date labels sit on a coloured background that the main pass turns black,
    # so read them again with a darker cut-off that keeps only the text.
    for psm in (6, 11):
        try:
            alt = _parse_rows(_ocr_rows(file_bytes, psm, thr=95))
        except Exception:
            continue
        if not alt:
            continue
        for i, b in enumerate(best):
            match = next((a for a in alt if a["production"] == b["production"]
                          and a["rej_in"] == b["rej_in"]), None)
            if match is None and len(alt) == len(best):
                match = alt[i]
            if match and match["label"] and len(match["label"]) > len(b["label"] or "") * 0 and not b.get("_label_ok"):
                if re.search(r"\d", match["label"]):
                    b["label"], b["_label_ok"] = match["label"], True
        if all(b.get("_label_ok") for b in best):
            break
    for b in best:
        if not b.get("_label_ok"):
            b["label"] = ""
        b.pop("_label_ok", None)
    return best


# ---------------------------------------------------------------- helpers ----
def split_total(blocks: list[dict]):
    """If the last block is the sum of the ones before it (the sheet's
    month-total row), separate it. Returns (weeks, total_or_None)."""
    if len(blocks) >= 2:
        rest = blocks[:-1]
        if blocks[-1]["production"] == sum(b["production"] for b in rest):
            return rest, blocks[-1]
    return blocks, None


def check_block(block: dict) -> str | None:
    """Cross-check extracted numbers with the sheet's own confirmed-rejection
    figure. Returns a warning string if they disagree."""
    src = block.get("confirmed_src")
    prod = block.get("production") or 0
    if src is None or not prod:
        return None
    calc = (block["rej_in"] - block["rej_out"]) / prod * 100
    if abs(calc - src) > 0.015:
        return f"calculated {calc:.2f}% but the file says {src:.2f}%"
    return None
