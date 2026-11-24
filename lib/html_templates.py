"""Builds the branded, downloadable HTML versions of both dashboards.

This is the same visual design used in the hand-built ICU dashboards
(Bebas Neue / DM Sans / DM Mono via Google Fonts, rounded cards, the
rejection/alteration color system). It is kept separate from the PNG
renderer (png_render.py), which uses a browser-free matplotlib replica so
that PNG export works reliably on Streamlit Community Cloud without a
headless-Chromium dependency.
"""
from __future__ import annotations

from .branding import (
    LOGO_BASE64, REJECTION, ALTERATION, ALTERATION_LIGHT, GREEN, TEXT,
    MUTED, ACCENT, BG, CARD, COMPANY_NAME,
)

_BASE_CSS = f"""
  :root {{
    --bg:{BG};--card:{CARD};--border:rgba(0,0,0,0.08);
    --rejection:{REJECTION};--alteration:{ALTERATION};--alteration-light:{ALTERATION_LIGHT};
    --green:{GREEN};--text:{TEXT};--muted:{MUTED};
    --accent:{ACCENT};--accent-bg:rgba(37,99,235,0.08);
  }}
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;padding:40px 28px 60px;}}
  .page{{max-width:1280px;margin:0 auto;}}
  .header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:30px;gap:16px;flex-wrap:wrap;}}
  .brand{{display:flex;align-items:center;gap:14px;}}
  .brand-icon{{width:56px;height:56px;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(37,99,235,0.15);flex-shrink:0;}}
  .brand-icon img{{width:56px;height:56px;object-fit:cover;display:block;}}
  .brand-text .company{{font-size:14px;letter-spacing:0.2em;text-transform:uppercase;color:var(--muted);font-weight:600;}}
  .brand-text .unit{{font-family:'Bebas Neue',sans-serif;font-size:34px;letter-spacing:0.05em;color:var(--text);line-height:1;}}
  .meta{{text-align:right;}}
  .meta .date-badge{{display:inline-block;background:var(--accent-bg);border:1px solid rgba(37,99,235,0.2);color:var(--accent);font-family:'DM Mono',monospace;font-size:16px;font-weight:700;padding:7px 18px;border-radius:20px;letter-spacing:0.05em;margin-bottom:7px;}}
  .meta .period{{font-size:20px;font-weight:700;color:var(--text);}}
  .title-strip{{display:flex;align-items:center;gap:16px;margin-bottom:30px;}}
  .title-strip h1{{font-family:'Bebas Neue',sans-serif;font-size:46px;letter-spacing:0.04em;color:var(--text);line-height:1;}}
  .title-strip .divider{{flex:1;height:2px;background:linear-gradient(90deg,rgba(0,0,0,0.08) 0%,transparent 100%);}}
  .section-label{{font-family:'Bebas Neue',sans-serif;font-size:24px;letter-spacing:0.06em;color:var(--accent);margin-bottom:16px;display:flex;align-items:center;gap:9px;}}
  .section-label .dot{{width:11px;height:11px;border-radius:50%;background:var(--accent);}}
  .kpi-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:38px;}}
  .kpi{{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:24px 20px;position:relative;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.06);}}
  .kpi::before{{content:'';position:absolute;top:0;left:0;right:0;height:4px;border-radius:18px 18px 0 0;}}
  .kpi.red::before{{background:var(--rejection);}}
  .kpi.green::before{{background:var(--green);}}
  .kpi.gold::before{{background:var(--alteration-light);}}
  .kpi.blue::before{{background:var(--accent);}}
  .kpi.dark::before{{background:var(--text);}}
  .kpi-label{{font-size:15px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;margin-bottom:10px;line-height:1.3;}}
  .kpi.red .kpi-label{{color:var(--rejection);}}
  .kpi.green .kpi-label{{color:var(--green);}}
  .kpi.gold .kpi-label{{color:var(--alteration);}}
  .kpi.blue .kpi-label{{color:var(--accent);}}
  .kpi.dark .kpi-label{{color:var(--text);}}
  .kpi-value{{font-family:'Bebas Neue',sans-serif;font-size:42px;letter-spacing:0.01em;line-height:1;}}
  .kpi.red .kpi-value{{color:var(--rejection);}}
  .kpi.green .kpi-value{{color:var(--green);}}
  .kpi.gold .kpi-value{{color:var(--alteration);}}
  .kpi.blue .kpi-value{{color:var(--accent);}}
  .kpi.dark .kpi-value{{color:var(--text);}}
  .kpi-sub{{font-size:15px;color:var(--muted);margin-top:6px;font-weight:600;}}
  .table-wrap{{background:var(--card);border:1px solid var(--border);border-radius:20px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.06);margin-bottom:30px;position:relative;}}
  table{{width:100%;border-collapse:collapse;}}
  thead tr.group-row th{{font-size:16px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;padding:15px 18px;text-align:center;border-bottom:1px solid var(--border);}}
  thead tr.group-row th.rej-head{{background:#fff2ef;color:var(--rejection);border-top:1px solid var(--rejection);}}
  thead tr.group-row th.alt-head{{background:#fffbf0;color:var(--alteration);border-top:1px solid var(--alteration);}}
  thead tr.group-row th.empty-head{{background:#f7f8fc;}}
  thead tr.group-row th.conf-head{{background:#fff2ef;color:var(--rejection);}}
  thead tr.sub-row th{{background:#f7f8fc;font-size:15px;font-weight:700;letter-spacing:0.03em;text-transform:uppercase;color:var(--muted);padding:14px 18px;text-align:center;border-bottom:2px solid var(--border);}}
  thead tr.sub-row th.week-col{{text-align:left;}}
  td{{padding:18px 18px;text-align:center;font-family:'DM Mono',monospace;font-size:21px;font-weight:700;border-top:1px solid var(--border);}}
  td.week-col{{text-align:left;font-family:'DM Sans',sans-serif;font-weight:800;font-size:18px;color:var(--text);}}
  td.week-col .range{{display:block;font-weight:600;color:var(--muted);font-size:15px;margin-top:3px;font-family:'DM Sans',sans-serif;}}
  td.pct-cell{{font-size:17px;font-weight:700;color:var(--muted);white-space:nowrap;}}
  tbody tr:nth-child(even){{background:#fafbfe;}}
  td.rej-in{{color:var(--rejection);}}
  td.rej-out{{color:var(--green);}}
  td.alt-in{{color:var(--alteration);}}
  td.alt-out{{color:var(--accent);}}
  td.conf{{font-weight:800;color:var(--rejection);font-size:23px;}}
  td.prod-cell{{color:var(--text);font-size:20px;}}
  tbody tr.total-row td{{font-weight:800;font-size:22px;border-top:2.5px solid #0f1828;background:linear-gradient(135deg,rgba(217,79,40,0.06),rgba(37,99,235,0.04));}}
  tbody tr.total-row td.week-col{{font-size:18px;}}
  tbody tr.total-row td.pct-cell{{font-size:17px;font-weight:800;white-space:nowrap;}}
  tbody tr.total-row td.conf{{font-size:25px;}}
  tbody tr:last-child td:nth-child(2),
  tbody tr:last-child td:nth-child(3),
  tbody tr:last-child td:nth-child(4){{border-bottom:1px solid var(--rejection);}}
  tbody tr:last-child td:nth-child(5),
  tbody tr:last-child td:nth-child(6),
  tbody tr:last-child td:nth-child(7){{border-bottom:1px solid var(--alteration);}}
  .vline{{position:absolute;top:0;bottom:0;width:1px;pointer-events:none;z-index:5;}}
  .vline.thick{{width:2px;}}
  .bottom-grid{{display:grid;grid-template-columns:1fr 1.6fr;gap:20px;}}
  .bottom-grid.single{{grid-template-columns:1fr;}}
  .banner-main{{background:linear-gradient(135deg,rgba(217,79,40,0.1),rgba(217,79,40,0.03));border:1.5px solid rgba(217,79,40,0.25);border-radius:18px;padding:28px 32px;box-shadow:0 2px 12px rgba(217,79,40,0.07);}}
  .banner-main.wide{{text-align:center;padding:34px 32px;}}
  .banner-main .bl{{font-size:15px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted);margin-bottom:10px;}}
  .banner-main .bv{{font-family:'Bebas Neue',sans-serif;font-size:72px;color:var(--rejection);line-height:1;}}
  .banner-main.wide .bv{{font-size:88px;}}
  .banner-weekly{{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:28px 32px;box-shadow:0 2px 12px rgba(0,0,0,0.06);}}
  .banner-weekly .bl{{font-size:15px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted);margin-bottom:18px;}}
  .week-pills{{display:grid;grid-template-columns:repeat(var(--npills,4),1fr);gap:14px;}}
  .week-pill{{text-align:center;}}
  .week-pill .wp-label{{font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);margin-bottom:8px;}}
  .week-pill .wp-val{{font-family:'DM Mono',monospace;font-size:28px;font-weight:800;color:var(--rejection);}}
  .footer{{margin-top:28px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;padding-top:18px;border-top:1px solid var(--border);}}
  .footer .sender{{font-size:15px;color:var(--muted);}}
  .footer .sender strong{{color:var(--text);}}
  .footer .stamp{{font-family:'DM Mono',monospace;font-size:14px;color:var(--muted);}}
  .split-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:30px;}}
  .mini-card{{background:var(--card);border:1px solid var(--border);border-radius:18px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.06);}}
  .mini-card .mc-head{{display:flex;align-items:center;gap:9px;padding:16px 20px;font-family:'Bebas Neue',sans-serif;font-size:22px;letter-spacing:0.05em;}}
  .mini-card.rej .mc-head{{color:var(--rejection);background:#fff2ef;}}
  .mini-card.alt .mc-head{{color:var(--alteration);background:#fffbf0;}}
  .mc-dot{{width:10px;height:10px;border-radius:50%;}}
  .mini-card.rej .mc-dot{{background:var(--rejection);}}
  .mini-card.alt .mc-dot{{background:var(--alteration);}}
  .mc-row{{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-top:1px solid var(--border);}}
  .mc-row .mc-label{{font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;color:var(--muted);}}
  .mc-row .mc-vals{{font-family:'DM Mono',monospace;font-size:19px;font-weight:700;display:flex;gap:18px;}}
  .mc-vals .v-in{{min-width:90px;text-align:right;}}
  .mini-card.rej .v-in{{color:var(--rejection);}}
  .mini-card.alt .v-in{{color:var(--alteration);}}
  .mc-vals .v-out{{min-width:90px;text-align:right;}}
  .mini-card.rej .v-out{{color:var(--green);}}
  .mini-card.alt .v-out{{color:var(--accent);}}
"""

_FONT_LINK = (
    '<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&'
    "family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500;600;700"
    '&display=swap" rel="stylesheet">'
)

_VLINE_SCRIPT = """
<script>
  function positionBlockLines(){
    var wrap = document.querySelector('.table-wrap');
    var row = wrap && wrap.querySelector('thead tr.sub-row');
    if(!row) return;
    var cells = row.children;
    var wrapRect = wrap.getBoundingClientRect();
    var rejLeft = cells[1].getBoundingClientRect().left - wrapRect.left;
    var midBoundary = cells[3].getBoundingClientRect().right - wrapRect.left;
    var altRight = cells[6].getBoundingClientRect().right - wrapRect.left;
    var l1 = document.getElementById('vline-rej-left');
    var l2 = document.getElementById('vline-mid');
    var l3 = document.getElementById('vline-alt-right');
    if(l1) l1.style.left = rejLeft + 'px';
    if(l2) l2.style.left = midBoundary + 'px';
    if(l3) l3.style.left = (altRight - 2) + 'px';
  }
  window.addEventListener('load', positionBlockLines);
  window.addEventListener('resize', positionBlockLines);
  if(document.fonts && document.fonts.ready){ document.fonts.ready.then(positionBlockLines); }
  setTimeout(positionBlockLines, 300);
</script>
"""


def _money(v: float) -> str:
    return f"{v:,.0f}"


def _p(v: float) -> str:
    return f"{v:.2f}%"


def build_monthly_html(ctx: dict) -> str:
    meta = ctx["meta"]
    weeks = ctx["weeks"]
    total = ctx["total"]

    week_rows = []
    for w in weeks:
        week_rows.append(f"""
        <tr>
          <td class="week-col">{w['label']}<span class="range">{w['range']}</span></td>
          <td class="rej-in">{_money(w['rej_in'])}</td>
          <td class="rej-out">{_money(w['rej_out'])}</td>
          <td class="pct-cell">{_p(w['rej_in_pct'])} / {_p(w['rej_out_pct'])}</td>
          <td class="alt-in">{_money(w['alt_in'])}</td>
          <td class="alt-out">{_money(w['alt_out'])}</td>
          <td class="pct-cell">{_p(w['alt_in_pct'])} / {_p(w['alt_out_pct'])}</td>
          <td class="prod-cell">{_money(w['production'])}</td>
          <td class="conf">{_p(w['confirmed_pct'])}</td>
        </tr>""")

    total_row = f"""
        <tr class="total-row">
          <td class="week-col">Monthly Total<span class="range">{total['range']}</span></td>
          <td class="rej-in">{_money(total['rej_in'])}</td>
          <td class="rej-out">{_money(total['rej_out'])}</td>
          <td class="pct-cell">{_p(total['rej_in_pct'])} / {_p(total['rej_out_pct'])}</td>
          <td class="alt-in">{_money(total['alt_in'])}</td>
          <td class="alt-out">{_money(total['alt_out'])}</td>
          <td class="pct-cell">{_p(total['alt_in_pct'])} / {_p(total['alt_out_pct'])}</td>
          <td class="prod-cell">{_money(total['production'])}</td>
          <td class="conf">{_p(total['confirmed_pct'])}</td>
        </tr>"""

    pills = "".join(
        f"""
        <div class="week-pill">
          <div class="wp-label">{w['label']}</div>
          <div class="wp-val">{_p(w['confirmed_pct'])}</div>
        </div>""" for w in weeks
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{_FONT_LINK}
<style>{_BASE_CSS}
  .week-pills{{--npills:{max(len(weeks),1)};}}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="brand">
      <div class="brand-icon"><img src="data:image/jpeg;base64,{LOGO_BASE64}" alt="AM Logo"></div>
      <div class="brand-text">
        <div class="company">{COMPANY_NAME}</div>
        <div class="unit">ICU &#8209; {meta['unit']}</div>
      </div>
    </div>
    <div class="meta">
      <div class="date-badge">MONTHLY SUMMARY</div>
      <div class="period">{meta['period']}</div>
    </div>
  </div>

  <div class="title-strip">
    <h1>Input vs Output Summary</h1>
    <div class="divider"></div>
  </div>

  <div class="section-label"><div class="dot"></div>{meta['month_label']} Totals</div>
  <div class="kpi-row">
    <div class="kpi red">
      <div class="kpi-label">Rejection In</div>
      <div class="kpi-value">{_money(total['rej_in'])}</div>
      <div class="kpi-sub">{_p(total['rej_in_pct'])} of production</div>
    </div>
    <div class="kpi green">
      <div class="kpi-label">Rejection Out</div>
      <div class="kpi-value">{_money(total['rej_out'])}</div>
      <div class="kpi-sub">{_p(total['rej_out_pct'])} of production</div>
    </div>
    <div class="kpi gold">
      <div class="kpi-label">Alteration In</div>
      <div class="kpi-value">{_money(total['alt_in'])}</div>
      <div class="kpi-sub">{_p(total['alt_in_pct'])} of production</div>
    </div>
    <div class="kpi blue">
      <div class="kpi-label">Alteration Out</div>
      <div class="kpi-value">{_money(total['alt_out'])}</div>
      <div class="kpi-sub">{_p(total['alt_out_pct'])} of production</div>
    </div>
    <div class="kpi dark">
      <div class="kpi-label">Total Production</div>
      <div class="kpi-value">{_money(total['production'])}</div>
      <div class="kpi-sub">Units &middot; {meta['month_label']}</div>
    </div>
  </div>

  <div class="section-label"><div class="dot"></div>Weekly Breakdown</div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr class="group-row">
          <th class="empty-head"></th>
          <th class="rej-head" colspan="3">Rejections</th>
          <th class="alt-head" colspan="3">Alterations</th>
          <th class="empty-head">Production</th>
          <th class="conf-head">Confirmed</th>
        </tr>
        <tr class="sub-row">
          <th class="week-col">Week</th>
          <th>In Qty</th><th>Out Qty</th><th>%</th>
          <th>In Qty</th><th>Out Qty</th><th>%</th>
          <th>Units</th>
          <th>Rejection</th>
        </tr>
      </thead>
      <tbody>{''.join(week_rows)}{total_row}
      </tbody>
    </table>
    <div class="vline" id="vline-rej-left" style="background:var(--rejection);"></div>
    <div class="vline" id="vline-mid" style="background:var(--rejection);"></div>
    <div class="vline thick" id="vline-alt-right" style="background:var(--alteration);"></div>
  </div>

  <div class="bottom-grid">
    <div class="banner-main">
      <div class="bl">Monthly Confirmed Rejection Rate</div>
      <div class="bv">{_p(total['confirmed_pct'])}</div>
    </div>
    <div class="banner-weekly">
      <div class="bl">Weekly Confirmed Rejection Rate</div>
      <div class="week-pills">{pills}
      </div>
    </div>
  </div>

  <div class="footer">
    <div class="sender">Prepared by <strong>{meta['prepared_by']}</strong> &middot; {meta['prepared_role']} &middot; {meta['prepared_email']}</div>
    <div class="stamp">Monthly Recap &middot; {meta['month_label']}</div>
  </div>
</div>
{_VLINE_SCRIPT}
</body>
</html>"""


def build_weekly_html(ctx: dict) -> str:
    meta = ctx["meta"]
    d = ctx["data"]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{_FONT_LINK}
<style>{_BASE_CSS}</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="brand">
      <div class="brand-icon"><img src="data:image/jpeg;base64,{LOGO_BASE64}" alt="AM Logo"></div>
      <div class="brand-text">
        <div class="company">{COMPANY_NAME}</div>
        <div class="unit">ICU &#8209; {meta['unit']}</div>
      </div>
    </div>
    <div class="meta">
      <div class="date-badge">WEEKLY SUMMARY</div>
      <div class="period">{meta['period']}</div>
    </div>
  </div>

  <div class="title-strip">
    <h1>Input vs Output Summary</h1>
    <div class="divider"></div>
  </div>

  <div class="kpi-row" style="grid-template-columns:repeat(5,1fr);">
    <div class="kpi red">
      <div class="kpi-label">Rejection In</div>
      <div class="kpi-value">{_money(d['rej_in'])}</div>
      <div class="kpi-sub">{_p(d['rej_in_pct'])} of production</div>
    </div>
    <div class="kpi green">
      <div class="kpi-label">Rejection Out</div>
      <div class="kpi-value">{_money(d['rej_out'])}</div>
      <div class="kpi-sub">{_p(d['rej_out_pct'])} of production</div>
    </div>
    <div class="kpi gold">
      <div class="kpi-label">Alteration In</div>
      <div class="kpi-value">{_money(d['alt_in'])}</div>
      <div class="kpi-sub">{_p(d['alt_in_pct'])} of production</div>
    </div>
    <div class="kpi blue">
      <div class="kpi-label">Alteration Out</div>
      <div class="kpi-value">{_money(d['alt_out'])}</div>
      <div class="kpi-sub">{_p(d['alt_out_pct'])} of production</div>
    </div>
    <div class="kpi dark">
      <div class="kpi-label">Total Production</div>
      <div class="kpi-value">{_money(d['production'])}</div>
      <div class="kpi-sub">Units &middot; {meta['period']}</div>
    </div>
  </div>

  <div class="split-grid">
    <div class="mini-card rej">
      <div class="mc-head"><div class="mc-dot"></div>Rejections</div>
      <div class="mc-row"><div class="mc-label">Units</div><div class="mc-vals"><div class="v-in">{_money(d['rej_in'])}</div><div class="v-out">{_money(d['rej_out'])}</div></div></div>
      <div class="mc-row"><div class="mc-label">Production</div><div class="mc-vals"><div class="v-in" style="color:var(--text)">{_money(d['production'])}</div><div class="v-out" style="color:var(--text)">{_money(d['production'])}</div></div></div>
      <div class="mc-row"><div class="mc-label">Percentage</div><div class="mc-vals"><div class="v-in">{_p(d['rej_in_pct'])}</div><div class="v-out">{_p(d['rej_out_pct'])}</div></div></div>
    </div>
    <div class="mini-card alt">
      <div class="mc-head"><div class="mc-dot"></div>Alterations</div>
      <div class="mc-row"><div class="mc-label">Units</div><div class="mc-vals"><div class="v-in">{_money(d['alt_in'])}</div><div class="v-out">{_money(d['alt_out'])}</div></div></div>
      <div class="mc-row"><div class="mc-label">Production</div><div class="mc-vals"><div class="v-in" style="color:var(--text)">{_money(d['production'])}</div><div class="v-out" style="color:var(--text)">{_money(d['production'])}</div></div></div>
      <div class="mc-row"><div class="mc-label">Percentage</div><div class="mc-vals"><div class="v-in">{_p(d['alt_in_pct'])}</div><div class="v-out">{_p(d['alt_out_pct'])}</div></div></div>
    </div>
  </div>

  <div class="bottom-grid single">
    <div class="banner-main wide">
      <div class="bl">Confirmed Rejection Rate</div>
      <div class="bv">{_p(d['confirmed_pct'])}</div>
    </div>
  </div>

  <div class="footer">
    <div class="sender">Prepared by <strong>{meta['prepared_by']}</strong> &middot; {meta['prepared_role']} &middot; {meta['prepared_email']}</div>
    <div class="stamp">Weekly Recap &middot; {meta['period']}</div>
  </div>
</div>
</body>
</html>"""
