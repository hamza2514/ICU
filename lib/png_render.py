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

W = 1360.0  # virtual canvas width (data units == px at dpi=160/136%... just a coordinate space)


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
          ha="left", va="top", letter_spacing_hint=False, **kw):
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
            family=family, ha=ha, va=va, zorder=5, **kw)


def _logo_image():
    try:
        from PIL import Image
        raw = base64.b64decode(LOGO_BASE64)
        return Image.open(io.BytesIO(raw))
    except Exception:
        return None


def _draw_header(ax, y0, unit_label, badge_text, period_text):
    """Returns the y coordinate just below the header."""
    logo_size = 56
    img = _logo_image()
    if img is not None:
        ax.imshow(img, extent=(28, 28 + logo_size, y0 + logo_size, y0), zorder=6)
        _rrect(ax, 28, y0, logo_size, logo_size, "none", radius=12,
               edgecolor="none", zorder=5)
    text_x = 28 + logo_size + 14
    _text(ax, text_x, y0 + 6, COMPANY_NAME, size=12, color=MUTED, weight="bold")
    _text(ax, text_x, y0 + 24, f"ICU - {unit_label}", size=27, color=TEXT, weight="bold")

    # right side badge + period
    badge_w = 190
    badge_x = W - 28 - badge_w
    _rrect(ax, badge_x, y0 - 2, badge_w, 30, "#e7edfc", radius=15)
    _text(ax, badge_x + badge_w / 2, y0 + 13, badge_text, size=12.5, color=ACCENT,
          weight="bold", family=F_MONO, ha="center", va="center")
    _text(ax, W - 28, y0 + 48, period_text, size=16, color=TEXT, weight="bold", ha="right")
    return y0 + logo_size + 20


def _draw_title(ax, y0):
    _text(ax, 28, y0 + 6, "Input vs Output Summary", size=32, color=TEXT, weight="bold")
    line_y = y0 + 50
    ax.add_line(Line2D([420, W - 28], [line_y, line_y], color="#d8dce8", linewidth=2, zorder=1))
    return y0 + 68


def _draw_section_label(ax, y0, label):
    ax.add_patch(plt.Circle((34, y0 + 11), 5.5, color=ACCENT, zorder=5))
    _text(ax, 48, y0 + 2, label.upper(), size=16, color=ACCENT, weight="bold")
    return y0 + 40


KPI_SPECS = [
    ("REJECTION IN", "rej_in", "rej_in_pct", REJECTION),
    ("REJECTION OUT", "rej_out", "rej_out_pct", GREEN),
    ("ALTERATION IN", "alt_in", "alt_in_pct", ALTERATION),
    ("ALTERATION OUT", "alt_out", "alt_out_pct", ACCENT),
]


def _draw_kpi_row(ax, y0, total, period_label, height=120):
    n = 5
    gap = 14
    cw = (W - 56 - gap * (n - 1)) / n
    x = 28
    specs = KPI_SPECS + [("TOTAL PRODUCTION", "production", None, TEXT)]
    for i, (label, key, pct_key, color) in enumerate(specs):
        _rrect(ax, x, y0, cw, height, CARD, radius=16, edgecolor="#e4e6ef", linewidth=1)
        _rrect(ax, x, y0, cw, 4, color, radius=2)
        _text(ax, x + 18, y0 + 24, label, size=10.5, color=color, weight="bold")
        value = _money(total[key])
        _text(ax, x + 18, y0 + 50, value, size=25, color=color, weight="bold")
        if pct_key:
            sub = f"{_p(total[pct_key])} of production"
        else:
            sub = f"Units · {period_label}"
        _text(ax, x + 18, y0 + 92, sub, size=10.5, color=MUTED, weight="bold")
        x += cw + gap
    return y0 + height + 30


def _draw_weekly_table(ax, y0, weeks, total, row_h=64):
    n = len(weeks)
    table_h = row_h * (n + 2) + 6
    _rrect(ax, 28, y0, W - 56, table_h, CARD, radius=18, edgecolor="#e4e6ef", linewidth=1)

    col_x = [28, 198, 388, 498, 688, 818, 948, 1058, 1178, W - 28]
    # columns: week | rejIn | rejOut | rej% | altIn | altOut | alt% | prod | conf
    headers_top = ["", "Rejections", "", "", "Alterations", "", "", "Production", "Confirmed"]
    header_h = row_h * 0.62

    _rrect(ax, col_x[1], y0, col_x[4] - col_x[1], header_h, "#fff2ef", radius=0)
    _rrect(ax, col_x[4], y0, col_x[7] - col_x[4], header_h, "#fffbf0", radius=0)
    _text(ax, (col_x[1] + col_x[4]) / 2, y0 + header_h / 2, "REJECTIONS", size=12.5,
          color=REJECTION, weight="bold", ha="center", va="center")
    _text(ax, (col_x[4] + col_x[7]) / 2, y0 + header_h / 2, "ALTERATIONS", size=12.5,
          color=ALTERATION, weight="bold", ha="center", va="center")

    sub_y = y0 + header_h
    sub_h = row_h * 0.62
    sub_labels = ["WEEK", "IN QTY", "OUT QTY", "%", "IN QTY", "OUT QTY", "%", "UNITS", "REJECTION"]
    for i, lbl in enumerate(sub_labels):
        cx = (col_x[i] + col_x[i + 1]) / 2 if i else col_x[0] + 12
        ha = "left" if i == 0 else "center"
        _text(ax, cx, sub_y + sub_h / 2, lbl, size=10.5, color=MUTED, weight="bold",
              ha=ha, va="center")
    ax.add_line(Line2D([28, W - 28], [sub_y + sub_h, sub_y + sub_h], color="#d8dce8",
                        linewidth=1.6, zorder=3))

    row_top = sub_y + sub_h
    for idx, w in enumerate(weeks):
        ry = row_top + idx * row_h
        if idx % 2 == 1:
            _rrect(ax, 28, ry, W - 56, row_h, "#fafbfe", radius=0)
        _text(ax, col_x[0] + 12, ry + row_h * 0.32, w["label"], size=13.5, color=TEXT, weight="bold")
        _text(ax, col_x[0] + 12, ry + row_h * 0.66, w["range"], size=10.5, color=MUTED)
        _text(ax, (col_x[1] + col_x[2]) / 2, ry + row_h / 2, _money(w["rej_in"]), size=14.5,
              color=REJECTION, weight="bold", family=F_MONO, ha="center", va="center")
        _text(ax, (col_x[2] + col_x[3]) / 2, ry + row_h / 2, _money(w["rej_out"]), size=14.5,
              color=GREEN, weight="bold", family=F_MONO, ha="center", va="center")
        _text(ax, (col_x[3] + col_x[4]) / 2, ry + row_h / 2,
              f"{_p(w['rej_in_pct'])}/{_p(w['rej_out_pct'])}", size=10.5, color=MUTED,
              weight="bold", family=F_MONO, ha="center", va="center")
        _text(ax, (col_x[4] + col_x[5]) / 2, ry + row_h / 2, _money(w["alt_in"]), size=14.5,
              color=ALTERATION, weight="bold", family=F_MONO, ha="center", va="center")
        _text(ax, (col_x[5] + col_x[6]) / 2, ry + row_h / 2, _money(w["alt_out"]), size=14.5,
              color=ACCENT, weight="bold", family=F_MONO, ha="center", va="center")
        _text(ax, (col_x[6] + col_x[7]) / 2, ry + row_h / 2,
              f"{_p(w['alt_in_pct'])}/{_p(w['alt_out_pct'])}", size=10.5, color=MUTED,
              weight="bold", family=F_MONO, ha="center", va="center")
        _text(ax, (col_x[7] + col_x[8]) / 2, ry + row_h / 2, _money(w["production"]), size=14.5,
              color=TEXT, weight="bold", family=F_MONO, ha="center", va="center")
        _text(ax, (col_x[8] + col_x[9]) / 2, ry + row_h / 2, _p(w["confirmed_pct"]), size=15.5,
              color=REJECTION, weight="bold", family=F_MONO, ha="center", va="center")

    # total row
    ty = row_top + n * row_h
    _rrect(ax, 28, ty, W - 56, row_h * 1.15, "#f6e9e4", radius=0)
    ax.add_line(Line2D([28, W - 28], [ty, ty], color=TEXT, linewidth=2.4, zorder=3))
    th = row_h * 1.15
    _text(ax, col_x[0] + 12, ty + th * 0.30, "Monthly Total", size=14.5, color=TEXT, weight="bold")
    _text(ax, col_x[0] + 12, ty + th * 0.66, total["range"], size=10.5, color=MUTED)
    _text(ax, (col_x[1] + col_x[2]) / 2, ty + th / 2, _money(total["rej_in"]), size=15.5,
          color=REJECTION, weight="bold", family=F_MONO, ha="center", va="center")
    _text(ax, (col_x[2] + col_x[3]) / 2, ty + th / 2, _money(total["rej_out"]), size=15.5,
          color=GREEN, weight="bold", family=F_MONO, ha="center", va="center")
    _text(ax, (col_x[3] + col_x[4]) / 2, ty + th / 2,
          f"{_p(total['rej_in_pct'])}/{_p(total['rej_out_pct'])}", size=11, color=MUTED,
          weight="bold", family=F_MONO, ha="center", va="center")
    _text(ax, (col_x[4] + col_x[5]) / 2, ty + th / 2, _money(total["alt_in"]), size=15.5,
          color=ALTERATION, weight="bold", family=F_MONO, ha="center", va="center")
    _text(ax, (col_x[5] + col_x[6]) / 2, ty + th / 2, _money(total["alt_out"]), size=15.5,
          color=ACCENT, weight="bold", family=F_MONO, ha="center", va="center")
    _text(ax, (col_x[6] + col_x[7]) / 2, ty + th / 2,
          f"{_p(total['alt_in_pct'])}/{_p(total['alt_out_pct'])}", size=11, color=MUTED,
          weight="bold", family=F_MONO, ha="center", va="center")
    _text(ax, (col_x[7] + col_x[8]) / 2, ty + th / 2, _money(total["production"]), size=15.5,
          color=TEXT, weight="bold", family=F_MONO, ha="center", va="center")
    _text(ax, (col_x[8] + col_x[9]) / 2, ty + th / 2, _p(total["confirmed_pct"]), size=17,
          color=REJECTION, weight="bold", family=F_MONO, ha="center", va="center")

    # block border overlays (rejection / alteration groups)
    full_table_bottom = ty + th
    ax.add_line(Line2D([col_x[1], col_x[1]], [y0, full_table_bottom], color=REJECTION, linewidth=1.4, zorder=6))
    ax.add_line(Line2D([col_x[4], col_x[4]], [y0, full_table_bottom], color=REJECTION, linewidth=1.4, zorder=6))
    ax.add_line(Line2D([col_x[4], col_x[4]], [y0, full_table_bottom], color=ALTERATION, linewidth=1.4, zorder=6,
                        linestyle=(0, (1, 100))))  # keep rejection line visually dominant at the shared edge
    ax.add_line(Line2D([col_x[7] - 1, col_x[7] - 1], [y0, full_table_bottom], color=ALTERATION, linewidth=2.0, zorder=6))

    return full_table_bottom + 30


def _draw_bottom_banner_monthly(ax, y0, weeks, total, height=200):
    left_w = (W - 56) * 0.38
    right_w = (W - 56) - left_w - 20
    _rrect(ax, 28, y0, left_w, height, "#fbece6", radius=18, edgecolor=REJECTION, linewidth=1.2)
    _text(ax, 28 + left_w / 2, y0 + 32, "MONTHLY CONFIRMED REJECTION RATE", size=11.5,
          color=MUTED, weight="bold", ha="center")
    _text(ax, 28 + left_w / 2, y0 + 128, _p(total["confirmed_pct"]), size=52, color=REJECTION,
          weight="bold", ha="center", va="center")

    rx = 28 + left_w + 20
    _rrect(ax, rx, y0, right_w, height, CARD, radius=18, edgecolor="#e4e6ef", linewidth=1)
    _text(ax, rx + 24, y0 + 32, "WEEKLY CONFIRMED REJECTION RATE", size=11.5, color=MUTED, weight="bold")
    n = max(len(weeks), 1)
    seg = right_w / n
    for i, w in enumerate(weeks):
        cx = rx + seg * i + seg / 2
        _text(ax, cx, y0 + 92, w["label"].upper(), size=10, color=MUTED, weight="bold", ha="center")
        _text(ax, cx, y0 + 128, _p(w["confirmed_pct"]), size=19, color=REJECTION, weight="bold",
              family=F_MONO, ha="center", va="center")
    return y0 + height + 24


def _render_with_autocrop(draw_fn, guess_h: float, dpi: int = 160) -> bytes:
    """Draws onto an oversized canvas (so no layout function has to predict
    exact pixel heights ahead of time), then crops the PNG to the actual
    content height that the draw pass reports back."""
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
    fig.savefig(buf, format="png", facecolor=BG)
    plt.close(fig)
    buf.seek(0)

    from PIL import Image
    img = Image.open(buf)
    px_h = int(img.height * (final_y / guess_h))
    px_h = min(max(px_h, 1), img.height)
    cropped = img.crop((0, 0, img.width, px_h))
    out = io.BytesIO()
    cropped.save(out, format="PNG")
    return out.getvalue()


def render_monthly_png(ctx: dict, dpi: int = 160) -> bytes:
    meta = ctx["meta"]
    weeks = ctx["weeks"]
    total = ctx["total"]
    row_h = 64

    def draw(ax):
        y = 28
        y = _draw_header(ax, y, meta["unit"], "MONTHLY SUMMARY", meta["period"])
        y = _draw_title(ax, y)
        y = _draw_section_label(ax, y, f"{meta['month_label']} Totals")
        y = _draw_kpi_row(ax, y, total, meta["month_label"])
        y = _draw_section_label(ax, y, "Weekly Breakdown")
        y = _draw_weekly_table(ax, y, weeks, total, row_h=row_h)
        y = _draw_bottom_banner_monthly(ax, y, weeks, total)
        return y - 4

    n = max(len(weeks), 1)
    guess_h = 900 + row_h * (n + 2)
    return _render_with_autocrop(draw, guess_h, dpi=dpi)


def _draw_weekly_minicards(ax, y0, d, height=210):
    gap = 20
    cw = (W - 56 - gap) / 2
    x1, x2 = 28, 28 + cw + gap

    def card(x, title, color, bg, in_v, out_v, in_c, out_c, prod, in_p, out_p):
        _rrect(ax, x, y0, cw, height, CARD, radius=16, edgecolor="#e4e6ef", linewidth=1)
        _rrect(ax, x, y0, cw, 46, bg, radius=16)
        _rrect(ax, x, y0 + 23, cw, 23, bg, radius=0)
        ax.add_patch(plt.Circle((x + 24, y0 + 23), 5, color=color, zorder=6))
        _text(ax, x + 38, y0 + 16, title, size=15, color=color, weight="bold")
        rows = [
            ("Units", _money(in_v), _money(out_v), in_c, out_c),
            ("Production", _money(d["production"]), _money(d["production"]), TEXT, TEXT),
            ("Percentage", _p(in_p), _p(out_p), in_c, out_c),
        ]
        ry = y0 + 46
        rh = (height - 46) / 3
        for i, (label, lv, rv, lc, rc) in enumerate(rows):
            yy = ry + i * rh
            if i:
                ax.add_line(Line2D([x, x + cw], [yy, yy], color="#eef0f6", linewidth=1, zorder=3))
            _text(ax, x + 20, yy + rh / 2, label.upper(), size=10.5, color=MUTED, weight="bold", va="center")
            _text(ax, x + cw - 170, yy + rh / 2, lv, size=14, color=lc, weight="bold",
                  family=F_MONO, ha="right", va="center")
            _text(ax, x + cw - 20, yy + rh / 2, rv, size=14, color=rc, weight="bold",
                  family=F_MONO, ha="right", va="center")

    card(x1, "Rejections", REJECTION, "#fff2ef", d["rej_in"], d["rej_out"],
         REJECTION, GREEN, d["production"], d["rej_in_pct"], d["rej_out_pct"])
    card(x2, "Alterations", ALTERATION, "#fffbf0", d["alt_in"], d["alt_out"],
         ALTERATION, ACCENT, d["production"], d["alt_in_pct"], d["alt_out_pct"])
    return y0 + height + 30


def render_weekly_png(ctx: dict, dpi: int = 160) -> bytes:
    meta = ctx["meta"]
    d = ctx["data"]

    def draw(ax):
        y = 28
        y = _draw_header(ax, y, meta["unit"], "WEEKLY SUMMARY", meta["period"])
        y = _draw_title(ax, y)
        y += 10
        y = _draw_kpi_row(ax, y, d, meta["period"])
        y = _draw_weekly_minicards(ax, y, d)

        banner_h = 190
        _rrect(ax, 28, y, W - 56, banner_h, "#fbece6", radius=18, edgecolor=REJECTION, linewidth=1.2)
        _text(ax, W / 2, y + 36, "CONFIRMED REJECTION RATE", size=13, color=MUTED,
              weight="bold", ha="center")
        _text(ax, W / 2, y + 125, _p(d["confirmed_pct"]), size=60, color=REJECTION,
              weight="bold", ha="center", va="center")
        y += banner_h + 24

        return y - 4

    return _render_with_autocrop(draw, guess_h=900, dpi=dpi)
