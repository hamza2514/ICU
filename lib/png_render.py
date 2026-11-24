"""Renders both dashboards as PNG images using matplotlib only.

Deliberately avoids a headless browser (Playwright/Chromium): those are
heavy, slow to install, and unreliable on Streamlit Community Cloud's free
tier. matplotlib ships as a normal pip wheel, bundles its own fonts, and
gives pixel-perfect, deterministic output -- so PNG export works the same
on every deploy with no system packages required.

Visual language intentionally mirrors the HTML version (same color
palette, same card/table structure) but is not a pixel-for-pixel clone --
font shapes differ because this uses matplotlib's bundled DejaVu family
instead of the Google-hosted Bebas Neue / DM Sans / DM Mono used in the
HTML download.
"""
from __future__ import annotations

import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D

from .branding import (
    LOGO_BASE64, REJECTION, ALTERATION, ALTERATION_LIGHT, GREEN, TEXT,
    MUTED, ACCENT, BG, CARD, COMPANY_NAME,
)

F_BOLD = "DejaVu Sans"
F_MONO = "DejaVu Sans Mono"

W = 1360.0  # virtual canvas width; 100 units == 1 inch of the figure
M = 40      # left/right page margin
_DPI = 160


def _money(v: float) -> str:
    return f"{v:,.0f}"


def _p(v: float) -> str:
    return f"{v:.2f}%"


def _rrect(ax, x, y, w, h, color, radius=14, **kw):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        linewidth=kw.pop("linewidth", 0),
        edgecolor=kw.pop("edgecolor", "none"),
        facecolor=color,
        zorder=kw.pop("zorder", 2),
        **kw,
    )
    ax.add_patch(box)
    return box


def _text(ax, x, y, s, size=14, color=TEXT, weight="normal", family=F_BOLD,
          ha="left", va="center", **kw):
    return ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
                   family=family, ha=ha, va=va, zorder=5, **kw)


def _tw(ax, s, size, weight="bold", family=F_BOLD) -> float:
    """Width of a string in canvas units (used so lines/boxes never collide
    with text, and long labels can be shrunk to fit their cell)."""
    t = ax.text(0, 0, s, fontsize=size, fontweight=weight, family=family)
    r = ax.figure.canvas.get_renderer()
    px = t.get_window_extent(r).width
    t.remove()
    return px * 100.0 / _DPI


def _fit_text(ax, x, y, s, max_w, size, min_size=6.5, **kw):
    """Draw text, shrinking the font until it fits max_w."""
    weight = kw.get("weight", "normal")
    family = kw.get("family", F_BOLD)
    while size > min_size and _tw(ax, s, size, weight, family) > max_w:
        size -= 0.5
    return _text(ax, x, y, s, size=size, **kw)


def _logo_image():
    try:
        from PIL import Image
        raw = base64.b64decode(LOGO_BASE64)
        return Image.open(io.BytesIO(raw))
    except Exception:
        return None


def _draw_header(ax, y0, unit_label, badge_text, period_text):
    """Returns the y coordinate just below the header."""
    logo_size = 58
    img = _logo_image()
    if img is not None:
        ax.imshow(img, extent=(M, M + logo_size, y0 + logo_size, y0), zorder=6)
        ax.set_xlim(0, W)
    tx = M + logo_size + 16
    _text(ax, tx, y0 + 12, COMPANY_NAME.upper(), size=11, color=MUTED, weight="bold")
    _text(ax, tx, y0 + 40, f"ICU - {unit_label}", size=27, color=TEXT, weight="bold")

    badge_w = max(190, _tw(ax, badge_text, 12, "bold", F_MONO) + 44)
    bx = W - M - badge_w
    _rrect(ax, bx, y0 - 2, badge_w, 32, "#e7edfc", radius=16)
    _text(ax, bx + badge_w / 2, y0 + 14, badge_text, size=12, color=ACCENT,
          weight="bold", family=F_MONO, ha="center")
    _fit_text(ax, W - M, y0 + 54, period_text, max_w=W - 2 * M - 420, size=16,
              color=TEXT, weight="bold", ha="right")
    return y0 + logo_size + 26


def _draw_title(ax, y0):
    title = "Input vs Output Summary"
    size = 32
    _text(ax, M, y0 + 24, title, size=size, color=TEXT, weight="bold")
    x_end = M + _tw(ax, title, size) + 28
    ax.add_line(Line2D([x_end, W - M], [y0 + 34, y0 + 34], color="#d8dce8",
                       linewidth=1.8, zorder=1))
    return y0 + 78


def _draw_section_label(ax, y0, label):
    ax.add_patch(plt.Circle((M + 6, y0 + 12), 5.5, color=ACCENT, zorder=5))
    _text(ax, M + 22, y0 + 12, label.upper(), size=15, color=ACCENT, weight="bold")
    return y0 + 42


KPI_SPECS = [
    ("REJECTION IN", "rej_in", "rej_in_pct", REJECTION),
    ("REJECTION OUT", "rej_out", "rej_out_pct", GREEN),
    ("ALTERATION IN", "alt_in", "alt_in_pct", ALTERATION),
    ("ALTERATION OUT", "alt_out", "alt_out_pct", ACCENT),
]


def _draw_kpi_row(ax, y0, total, period_label, height=128):
    n = 5
    gap = 16
    cw = (W - 2 * M - gap * (n - 1)) / n
    x = M
    specs = KPI_SPECS + [("TOTAL PRODUCTION", "production", None, TEXT)]
    for label, key, pct_key, color in specs:
        _rrect(ax, x, y0, cw, height, CARD, radius=16, edgecolor="#e4e6ef", linewidth=1)
        _rrect(ax, x, y0, cw, 5, color, radius=2)
        _text(ax, x + 20, y0 + 30, label, size=10.5, color=color, weight="bold")
        _fit_text(ax, x + 20, y0 + 66, _money(total[key]), max_w=cw - 40, size=25,
                  color=color, weight="bold")
        sub = f"{_p(total[pct_key])} of production" if pct_key else f"Units · {period_label}"
        _fit_text(ax, x + 20, y0 + 106, sub, max_w=cw - 40, size=10.5, color=MUTED, weight="bold")
        x += cw + gap
    return y0 + height + 34


# table geometry: week | rejIn rejOut rej% | altIn altOut alt% | production | confirmed
_COL_W = [210, 110, 110, 160, 120, 120, 180, 135, 135]


def _col_x():
    xs = [M]
    for w in _COL_W:
        xs.append(xs[-1] + w)
    return xs


def _draw_weekly_table(ax, y0, weeks, total, row_h=74):
    cx = _col_x()
    tx0, tx1 = cx[0], cx[-1]          # table left/right edges
    head_h, sub_h, tot_h = 54, 50, 88
    n = len(weeks)
    table_h = head_h + sub_h + n * row_h + tot_h
    bottom = y0 + table_h
    _rrect(ax, tx0, y0, tx1 - tx0, table_h, CARD, radius=18, edgecolor="#e4e6ef", linewidth=1)

    # --- header band
    _rrect(ax, cx[1], y0, cx[4] - cx[1], head_h, "#fff2ef", radius=0)
    _rrect(ax, cx[4], y0, cx[7] - cx[4], head_h, "#fffbf0", radius=0)
    _rrect(ax, cx[8], y0, cx[9] - cx[8], head_h, "#fff2ef", radius=0)
    # keep the table's rounded top-right corner clean
    _text(ax, (cx[1] + cx[4]) / 2, y0 + head_h / 2, "REJECTIONS", size=12, color=REJECTION,
          weight="bold", ha="center")
    _text(ax, (cx[4] + cx[7]) / 2, y0 + head_h / 2, "ALTERATIONS", size=12, color=ALTERATION,
          weight="bold", ha="center")
    _text(ax, (cx[7] + cx[8]) / 2, y0 + head_h / 2, "PRODUCTION", size=10.5, color=TEXT,
          weight="bold", ha="center")
    _text(ax, (cx[8] + cx[9]) / 2, y0 + head_h / 2, "CONFIRMED", size=10.5, color=REJECTION,
          weight="bold", ha="center")

    sy = y0 + head_h
    _rrect(ax, tx0 + 1, sy, tx1 - tx0 - 2, sub_h, "#f9fafd", radius=0)
    labels = ["WEEK", "IN QTY", "OUT QTY", "%", "IN QTY", "OUT QTY", "%", "UNITS", "REJECTION"]
    for i, lbl in enumerate(labels):
        if i == 0:
            _text(ax, tx0 + 20, sy + sub_h / 2, lbl, size=10.5, color=MUTED, weight="bold")
        else:
            _text(ax, (cx[i] + cx[i + 1]) / 2, sy + sub_h / 2, lbl, size=10.5, color=MUTED,
                  weight="bold", ha="center")
    ax.add_line(Line2D([tx0, tx1], [sy + sub_h, sy + sub_h], color="#d8dce8", linewidth=1.6, zorder=3))

    def cells(r, yc, big, pct_size, conf_size, bold_total=False):
        def mid(i):
            return (cx[i] + cx[i + 1]) / 2
        m = dict(weight="bold", family=F_MONO, ha="center")
        _text(ax, mid(1), yc, _money(r["rej_in"]), size=big, color=REJECTION, **m)
        _text(ax, mid(2), yc, _money(r["rej_out"]), size=big, color=GREEN, **m)
        _fit_text(ax, mid(3), yc, f"{_p(r['rej_in_pct'])} / {_p(r['rej_out_pct'])}",
                  max_w=_COL_W[3] - 24, size=pct_size, color=MUTED, **m)
        _text(ax, mid(4), yc, _money(r["alt_in"]), size=big, color=ALTERATION, **m)
        _text(ax, mid(5), yc, _money(r["alt_out"]), size=big, color=ACCENT, **m)
        _fit_text(ax, mid(6), yc, f"{_p(r['alt_in_pct'])} / {_p(r['alt_out_pct'])}",
                  max_w=_COL_W[6] - 24, size=pct_size, color=MUTED, **m)
        _text(ax, mid(7), yc, _money(r["production"]), size=big, color=TEXT, **m)
        _text(ax, mid(8), yc, _p(r["confirmed_pct"]), size=conf_size, color=REJECTION, **m)

    top = sy + sub_h
    cell_w = _COL_W[0] - 36
    for i, w in enumerate(weeks):
        ry = top + i * row_h
        if i % 2 == 1:
            _rrect(ax, tx0 + 1, ry, tx1 - tx0 - 2, row_h, "#fafbfe", radius=0)
        _fit_text(ax, tx0 + 20, ry + row_h * 0.36, w["label"], max_w=cell_w, size=13,
                  color=TEXT, weight="bold")
        _fit_text(ax, tx0 + 20, ry + row_h * 0.66, w["range"], max_w=cell_w, size=9.5, color=MUTED)
        cells(w, ry + row_h / 2, 13, 9.5, 14)
        if i:
            ax.add_line(Line2D([tx0, tx1], [ry, ry], color="#eef0f6", linewidth=1, zorder=3))

    ty = top + n * row_h
    _rrect(ax, tx0 + 1, ty, tx1 - tx0 - 2, tot_h - 1, "#f8ebe7", radius=0)
    ax.add_line(Line2D([tx0, tx1], [ty, ty], color=TEXT, linewidth=2.2, zorder=3))
    _fit_text(ax, tx0 + 20, ty + tot_h * 0.36, "Monthly Total", max_w=cell_w, size=14, color=TEXT, weight="bold")
    _fit_text(ax, tx0 + 20, ty + tot_h * 0.67, total["range"], max_w=cell_w, size=9.5, color=MUTED)
    cells(total, ty + tot_h / 2, 14, 10, 15.5)

    # --- thin rectangular borders: one around Rejections, one around Alterations
    lw = 1.1
    for a, b, col, rlw in ((cx[1], cx[4], REJECTION, lw), (cx[4], cx[7], ALTERATION, 1.9)):
        ax.add_patch(plt.Rectangle((a, y0), b - a, table_h, fill=False, edgecolor=col,
                                   linewidth=lw, zorder=7))
        ax.add_line(Line2D([b, b], [y0, bottom], color=col, linewidth=rlw, zorder=8))

    return bottom + 34


def _draw_bottom_banner_monthly(ax, y0, weeks, total, height=170):
    inner = W - 2 * M
    left_w = inner * 0.38
    right_w = inner - left_w - 20
    _rrect(ax, M, y0, left_w, height, "#fbece6", radius=18, edgecolor=REJECTION, linewidth=1.2)
    _text(ax, M + left_w / 2, y0 + 36, "MONTHLY CONFIRMED REJECTION RATE", size=11,
          color=MUTED, weight="bold", ha="center")
    _text(ax, M + left_w / 2, y0 + 108, _p(total["confirmed_pct"]), size=50, color=REJECTION,
          weight="bold", ha="center")

    rx = M + left_w + 20
    _rrect(ax, rx, y0, right_w, height, CARD, radius=18, edgecolor="#e4e6ef", linewidth=1)
    _text(ax, rx + 28, y0 + 36, "WEEKLY CONFIRMED REJECTION RATE", size=11, color=MUTED, weight="bold")
    n = max(len(weeks), 1)
    seg = (right_w - 56) / n
    for i, w in enumerate(weeks):
        cxm = rx + 28 + seg * i + seg / 2
        _fit_text(ax, cxm, y0 + 94, w["label"].upper(), max_w=seg - 12, size=10,
                  color=MUTED, weight="bold", ha="center")
        _text(ax, cxm, y0 + 128, _p(w["confirmed_pct"]), size=19, color=REJECTION, weight="bold",
              family=F_MONO, ha="center")
    return y0 + height + 40


def _render_with_autocrop(draw_fn, guess_h: float, dpi: int = 160) -> bytes:
    """Draws onto an oversized canvas (so no layout function has to predict
    exact pixel heights ahead of time), then crops the PNG to the actual
    content height that the draw pass reports back."""
    global _DPI
    _DPI = dpi
    fig = plt.figure(figsize=(W / 100, guess_h / 100), dpi=dpi)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, W)
    ax.set_ylim(0, guess_h)
    ax.invert_yaxis()
    ax.axis("off")
    ax.set_facecolor(BG)

    final_y = draw_fn(ax)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=BG, dpi=dpi)
    plt.close(fig)
    buf.seek(0)

    from PIL import Image
    img = Image.open(buf)
    px_h = int(img.height * (final_y / guess_h))
    px_h = min(max(px_h, 1), img.height)
    out = io.BytesIO()
    img.crop((0, 0, img.width, px_h)).save(out, format="PNG")
    return out.getvalue()


def render_monthly_png(ctx: dict, dpi: int = 160) -> bytes:
    meta = ctx["meta"]
    weeks = ctx["weeks"]
    total = ctx["total"]
    row_h = 64

    def draw(ax):
        y = 40
        y = _draw_header(ax, y, meta["unit"], "MONTHLY SUMMARY", meta["period"])
        y = _draw_title(ax, y)
        y = _draw_section_label(ax, y, f"{meta['month_label']} Totals")
        y = _draw_kpi_row(ax, y, total, meta["month_label"])
        y = _draw_section_label(ax, y, "Weekly Breakdown")
        y = _draw_weekly_table(ax, y, weeks, total, row_h=row_h)
        y = _draw_bottom_banner_monthly(ax, y, weeks, total)
        return y

    n = max(len(weeks), 1)
    guess_h = 1100 + row_h * (n + 2)
    return _render_with_autocrop(draw, guess_h, dpi=dpi)


def _draw_weekly_minicards(ax, y0, d, height=216):
    gap = 20
    cw = (W - 2 * M - gap) / 2
    x1, x2 = M, M + cw + gap
    head = 52

    def card(x, title, color, bg, in_v, out_v, in_c, out_c, in_p, out_p):
        _rrect(ax, x, y0, cw, height, CARD, radius=16, edgecolor="#e4e6ef", linewidth=1)
        _rrect(ax, x + 1, y0 + 1, cw - 2, head, bg, radius=15)
        _rrect(ax, x + 1, y0 + head / 2, cw - 2, head / 2, bg, radius=0)
        ax.add_patch(plt.Circle((x + 28, y0 + head / 2), 5, color=color, zorder=6))
        _text(ax, x + 44, y0 + head / 2, title, size=15, color=color, weight="bold")
        rows = [
            ("Units", _money(in_v), _money(out_v), in_c, out_c),
            ("Production", _money(d["production"]), _money(d["production"]), TEXT, TEXT),
            ("Percentage", _p(in_p), _p(out_p), in_c, out_c),
        ]
        rh = (height - head) / 3
        for i, (label, lv, rv, lc, rc) in enumerate(rows):
            yy = y0 + head + i * rh
            ax.add_line(Line2D([x + 1, x + cw - 1], [yy, yy], color="#eef0f6", linewidth=1, zorder=3))
            _text(ax, x + 24, yy + rh / 2, label.upper(), size=10.5, color=MUTED, weight="bold")
            _text(ax, x + cw - 190, yy + rh / 2, lv, size=14, color=lc, weight="bold",
                  family=F_MONO, ha="right")
            _text(ax, x + cw - 24, yy + rh / 2, rv, size=14, color=rc, weight="bold",
                  family=F_MONO, ha="right")

    card(x1, "Rejections", REJECTION, "#fff2ef", d["rej_in"], d["rej_out"],
         REJECTION, GREEN, d["rej_in_pct"], d["rej_out_pct"])
    card(x2, "Alterations", ALTERATION, "#fffbf0", d["alt_in"], d["alt_out"],
         ALTERATION, ACCENT, d["alt_in_pct"], d["alt_out_pct"])
    return y0 + height + 34


def render_weekly_png(ctx: dict, dpi: int = 160) -> bytes:
    meta = ctx["meta"]
    d = ctx["data"]

    def draw(ax):
        y = 40
        y = _draw_header(ax, y, meta["unit"], "WEEKLY SUMMARY", meta["period"])
        y = _draw_title(ax, y)
        y = _draw_kpi_row(ax, y, d, meta["period"])
        y = _draw_weekly_minicards(ax, y, d)

        bh = 180
        _rrect(ax, M, y, W - 2 * M, bh, "#fbece6", radius=18, edgecolor=REJECTION, linewidth=1.2)
        _text(ax, W / 2, y + 40, "CONFIRMED REJECTION RATE", size=12, color=MUTED,
              weight="bold", ha="center")
        _text(ax, W / 2, y + 112, _p(d["confirmed_pct"]), size=56, color=REJECTION,
              weight="bold", ha="center")
        return y + bh + 40

    return _render_with_autocrop(draw, guess_h=1100, dpi=dpi)
