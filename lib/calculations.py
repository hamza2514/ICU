"""Pure calculation helpers shared by the monthly and weekly dashboards.

All percentages are derived from four raw inputs per period:
    production, rejection_in, rejection_out, alteration_in, alteration_out

Formulas (reverse engineered from the unit's historical reports and verified
against every historical period supplied by the user):
    rejection_in_pct   = rejection_in   / production * 100
    rejection_out_pct  = rejection_out  / production * 100
    alteration_in_pct  = alteration_in  / production * 100
    alteration_out_pct = alteration_out / production * 100
    confirmed_pct      = (rejection_in - rejection_out) / production * 100
"""
from __future__ import annotations


def pct(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return numerator / denominator * 100.0


def compute_period(row: dict) -> dict:
    """Given raw numbers for one period (a week, or a whole month), return a
    new dict with the raw numbers plus every derived percentage."""
    production = float(row.get("production") or 0)
    rej_in = float(row.get("rej_in") or 0)
    rej_out = float(row.get("rej_out") or 0)
    alt_in = float(row.get("alt_in") or 0)
    alt_out = float(row.get("alt_out") or 0)

    out = dict(row)
    out.update(
        production=production,
        rej_in=rej_in,
        rej_out=rej_out,
        alt_in=alt_in,
        alt_out=alt_out,
        rej_in_pct=pct(rej_in, production),
        rej_out_pct=pct(rej_out, production),
        alt_in_pct=pct(alt_in, production),
        alt_out_pct=pct(alt_out, production),
        confirmed_pct=pct(rej_in - rej_out, production),
    )
    return out


def compute_monthly(week_rows: list[dict]) -> dict:
    """week_rows: list of raw dicts each with label, range, production,
    rej_in, rej_out, alt_in, alt_out (already filtered to valid rows).
    Returns {"weeks": [...computed...], "total": {...computed...}}.
    The monthly total is the straight sum of the raw weekly numbers, which
    is how the source reports were built (always ties out exactly)."""
    weeks = [compute_period(r) for r in week_rows]

    total_raw = {
        "label": "Monthly Total",
        "range": week_rows[0].get("total_range", "") if week_rows else "",
        "production": sum(w["production"] for w in weeks),
        "rej_in": sum(w["rej_in"] for w in weeks),
        "rej_out": sum(w["rej_out"] for w in weeks),
        "alt_in": sum(w["alt_in"] for w in weeks),
        "alt_out": sum(w["alt_out"] for w in weeks),
    }
    total = compute_period(total_raw)
    return {"weeks": weeks, "total": total}
