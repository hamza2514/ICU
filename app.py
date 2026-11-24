"""ICU Dashboard Studio
Streamlit multi-user app for building the Monthly & Weekly ICU dashboards.

Deploy: push this whole folder to a GitHub repo and point Streamlit
Community Cloud at app.py. No local setup, no system packages required.
"""
from __future__ import annotations

import calendar
import io
from datetime import date

import pandas as pd
import streamlit as st

from lib import store, auth
from lib.branding import APP_TITLE, COMPANY_NAME, ACCENT
from lib.calculations import compute_monthly, compute_period
from lib.html_templates import build_monthly_html, build_weekly_html
from lib.png_render import render_monthly_png, render_weekly_png

st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide")

MONTH_NAMES = list(calendar.month_name)[1:]


# --------------------------------------------------------------------- CSS --
def inject_css():
    st.markdown(
        f"""
        <style>
        .block-container {{ padding-top: 2rem; max-width: 1200px; }}
        .am-brand {{ display:flex; align-items:center; gap:10px; margin-bottom: 0.5rem; }}
        .am-brand .dot {{ width:12px; height:12px; border-radius:50%; background:{ACCENT}; }}
        div[data-testid="stForm"] {{ border:1px solid rgba(0,0,0,0.08); border-radius:14px; padding:1.4rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------- bootstrap ----
def ensure_default_units():
    if not store.load_units():
        store.save_units(["AM-04"])


# ---------------------------------------------------------- initial setup --
def render_initial_setup():
    st.markdown(f"## 👋 Welcome to {APP_TITLE}")
    st.write(
        "No admin account exists yet. Create the first **Admin** account to get "
        "started — you'll be able to add units and create other user accounts "
        "from inside the app afterwards."
    )
    with st.form("setup_admin_form"):
        col1, col2 = st.columns(2)
        username = col1.text_input("Admin username")
        full_name = col2.text_input("Full name", value="")
        email = st.text_input("Email (used on dashboard footers)")
        col3, col4 = st.columns(2)
        password = col3.text_input("Password", type="password")
        password2 = col4.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create admin account", type="primary")

    if submitted:
        if not username or not password:
            st.error("Username and password are required.")
        elif password != password2:
            st.error("Passwords do not match.")
        elif len(password) < 6:
            st.error("Use a password of at least 6 characters.")
        elif store.get_user(username):
            st.error("That username already exists.")
        else:
            salt, pw_hash = auth.hash_password(password)
            store.upsert_user(username, {
                "password_salt": salt,
                "password_hash": pw_hash,
                "role": "admin",
                "full_name": full_name or username,
                "email": email,
                "units": [],  # admins implicitly see all units
                "active": True,
                "created_at": store.now_iso(),
                "must_change_password": False,
            })
            ensure_default_units()
            st.success("Admin account created. Please log in below.")
            st.rerun()


# -------------------------------------------------------------------- login
def render_login():
    left, mid, right = st.columns([1, 1.3, 1])
    with mid:
        st.markdown(
            f"<div class='am-brand'><div class='dot'></div>"
            f"<b>{COMPANY_NAME}</b></div>", unsafe_allow_html=True,
        )
        st.markdown(f"## {APP_TITLE}")
        st.caption("Sign in to build and download your ICU dashboards.")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if submitted:
            user = store.get_user(username)
            if not user or not user.get("active", True):
                st.error("Invalid username or password.")
            elif not auth.verify_password(password, user["password_salt"], user["password_hash"]):
                st.error("Invalid username or password.")
            else:
                st.session_state["user"] = {"username": username, **user}
                st.rerun()


# ------------------------------------------------------------- unit access --
def available_units(user: dict) -> list[str]:
    all_units = store.load_units()
    if user.get("role") == "admin":
        return all_units
    assigned = user.get("units", [])
    return [u for u in all_units if u in assigned]


def ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ----------------------------------------------------------- monthly tab ----
def _empty_week_df(n=4):
    return pd.DataFrame([
        {"Week Label": f"Week {i+1}", "Date Range": "", "Production": 0,
         "Rejection In": 0, "Rejection Out": 0, "Alteration In": 0, "Alteration Out": 0}
        for i in range(n)
    ])


def _record_to_df(record: dict) -> pd.DataFrame:
    rows = []
    for w in record.get("weeks", []):
        rows.append({
            "Week Label": w.get("label", ""), "Date Range": w.get("range", ""),
            "Production": w.get("production", 0), "Rejection In": w.get("rej_in", 0),
            "Rejection Out": w.get("rej_out", 0), "Alteration In": w.get("alt_in", 0),
            "Alteration Out": w.get("alt_out", 0),
        })
    return pd.DataFrame(rows) if rows else _empty_week_df()


def render_monthly_tab(user: dict):
    units = available_units(user)
    if not units:
        if user.get("role") == "admin":
            st.warning("No units exist yet. Add one in the Admin Panel tab first.")
        else:
            st.warning("No unit has been assigned to your account yet. Ask your admin to assign one.")
        return

    col1, col2, col3 = st.columns([1.2, 1, 1])
    unit = col1.selectbox("Unit", units, key="monthly_unit")
    month_name = col2.selectbox("Month", MONTH_NAMES, index=date.today().month - 1, key="monthly_month")
    year = col3.number_input("Year", min_value=2020, max_value=2100, value=date.today().year, step=1, key="monthly_year")
    month_num = MONTH_NAMES.index(month_name) + 1
    month_key = f"{year:04d}-{month_num:02d}"
    record_key = f"{unit}|{month_key}"

    existing = store.get_monthly_record(record_key)
    if existing:
        st.info(f"A saved record already exists for {unit} · {month_name} {year}. Editing it below will overwrite it when you regenerate.")

    with st.expander("Prepared-by details", expanded=False):
        pb_col1, pb_col2, pb_col3 = st.columns(3)
        prepared_by = pb_col1.text_input("Prepared by", value=existing.get("meta", {}).get("prepared_by") if existing else user.get("full_name", ""), key="monthly_prepared_by")
        prepared_role = pb_col2.text_input("Role", value=existing.get("meta", {}).get("prepared_role") if existing else f"IE Manager {unit}", key="monthly_prepared_role")
        prepared_email = pb_col3.text_input("Email", value=existing.get("meta", {}).get("prepared_email") if existing else user.get("email", ""), key="monthly_prepared_email")

    last_day = calendar.monthrange(year, month_num)[1]
    total_range_default = existing.get("meta", {}).get("total_range") if existing else f"1st – {ordinal(last_day)} {month_name} {year}"
    total_range = st.text_input("Monthly total date-range label", value=total_range_default, key="monthly_total_range")

    st.markdown("##### Weekly inputs")
    st.caption("Add or remove rows for however many periods this month needs. Percentages, confirmed-rejection rate, and the monthly total are all calculated automatically.")

    default_df = _record_to_df(existing) if existing else _empty_week_df()
    editor_key = f"monthly_editor_{record_key}"
    edited_df = st.data_editor(
        default_df,
        num_rows="dynamic",
        use_container_width=True,
        key=editor_key,
        column_config={
            "Week Label": st.column_config.TextColumn(width="small"),
            "Date Range": st.column_config.TextColumn(width="medium"),
            "Production": st.column_config.NumberColumn(min_value=0, step=1),
            "Rejection In": st.column_config.NumberColumn(min_value=0, step=1),
            "Rejection Out": st.column_config.NumberColumn(min_value=0, step=1),
            "Alteration In": st.column_config.NumberColumn(min_value=0, step=1),
            "Alteration Out": st.column_config.NumberColumn(min_value=0, step=1),
        },
    )

    generate = st.button("Generate monthly dashboard", type="primary", key="monthly_generate")

    state_key = f"monthly_ctx_{record_key}"
    if generate:
        rows = []
        for _, r in edited_df.iterrows():
            if not str(r.get("Week Label", "")).strip():
                continue
            rows.append({
                "label": str(r["Week Label"]).strip(),
                "range": str(r.get("Date Range", "")).strip(),
                "production": float(r.get("Production") or 0),
                "rej_in": float(r.get("Rejection In") or 0),
                "rej_out": float(r.get("Rejection Out") or 0),
                "alt_in": float(r.get("Alteration In") or 0),
                "alt_out": float(r.get("Alteration Out") or 0),
                "total_range": total_range,
            })
        if not rows:
            st.error("Add at least one week with a label before generating.")
        else:
            calc = compute_monthly(rows)
            calc["meta"] = {
                "unit": unit,
                "period": total_range,
                "month_label": f"{month_name} {year}",
                "prepared_by": prepared_by,
                "prepared_role": prepared_role,
                "prepared_email": prepared_email,
                "total_range": total_range,
            }
            store.save_monthly_record(record_key, {
                "meta": calc["meta"],
                "weeks": rows,
            })
            st.session_state[state_key] = calc
            st.success("Dashboard generated and saved.")

    ctx = st.session_state.get(state_key)
    if ctx:
        _render_dashboard_preview(ctx, user, kind="monthly", file_stub=f"ICU_{unit}_{month_key}_Monthly")


# ------------------------------------------------------------ weekly tab ----
def render_weekly_tab(user: dict):
    units = available_units(user)
    if not units:
        if user.get("role") == "admin":
            st.warning("No units exist yet. Add one in the Admin Panel tab first.")
        else:
            st.warning("No unit has been assigned to your account yet. Ask your admin to assign one.")
        return

    col1, col2 = st.columns([1, 2])
    unit = col1.selectbox("Unit", units, key="weekly_unit")
    period_label = col2.text_input("Date range label (e.g. 11th – 27th July 2026)", key="weekly_period")

    record_key = f"{unit}|{period_label}" if period_label else None
    existing = store.get_weekly_record(record_key) if record_key else None

    with st.expander("Prepared-by details", expanded=False):
        pb_col1, pb_col2, pb_col3 = st.columns(3)
        prepared_by = pb_col1.text_input("Prepared by", value=existing.get("meta", {}).get("prepared_by") if existing else user.get("full_name", ""), key="weekly_prepared_by")
        prepared_role = pb_col2.text_input("Role", value=existing.get("meta", {}).get("prepared_role") if existing else f"IE Manager {unit}", key="weekly_prepared_role")
        prepared_email = pb_col3.text_input("Email", value=existing.get("meta", {}).get("prepared_email") if existing else user.get("email", ""), key="weekly_prepared_email")

    st.markdown("##### Period inputs")
    d = existing.get("data", {}) if existing else {}
    c1, c2, c3, c4, c5 = st.columns(5)
    production = c1.number_input("Production", min_value=0, value=int(d.get("production", 0)), step=1)
    rej_in = c2.number_input("Rejection In", min_value=0, value=int(d.get("rej_in", 0)), step=1)
    rej_out = c3.number_input("Rejection Out", min_value=0, value=int(d.get("rej_out", 0)), step=1)
    alt_in = c4.number_input("Alteration In", min_value=0, value=int(d.get("alt_in", 0)), step=1)
    alt_out = c5.number_input("Alteration Out", min_value=0, value=int(d.get("alt_out", 0)), step=1)

    generate = st.button("Generate weekly dashboard", type="primary", key="weekly_generate")

    state_key = f"weekly_ctx_{unit}"
    if generate:
        if not period_label.strip():
            st.error("Enter a date-range label first (e.g. '11th – 27th July 2026').")
        else:
            data = compute_period({
                "production": production, "rej_in": rej_in, "rej_out": rej_out,
                "alt_in": alt_in, "alt_out": alt_out,
            })
            meta = {
                "unit": unit, "period": period_label,
                "prepared_by": prepared_by, "prepared_role": prepared_role,
                "prepared_email": prepared_email,
            }
            ctx = {"meta": meta, "data": data}
            store.save_weekly_record(record_key, {"meta": meta, "data": data})
            st.session_state[state_key] = ctx
            st.success("Dashboard generated and saved.")

    ctx = st.session_state.get(state_key)
    if ctx:
        safe_period = "".join(c if c.isalnum() else "_" for c in ctx["meta"]["period"])[:40]
        _render_dashboard_preview(ctx, user, kind="weekly", file_stub=f"ICU_{unit}_{safe_period}_Weekly")


# ------------------------------------------------------------ shared view --
def _render_dashboard_preview(ctx: dict, user: dict, kind: str, file_stub: str):
    st.markdown("---")
    st.markdown("##### Preview")

    if kind == "monthly":
        html_str = build_monthly_html(ctx)
        png_bytes = render_monthly_png(ctx)
    else:
        html_str = build_weekly_html(ctx)
        png_bytes = render_weekly_png(ctx)

    tab_png, tab_html = st.tabs(["PNG preview", "Full-design HTML preview"])
    with tab_png:
        st.image(png_bytes, use_container_width=True)
    with tab_html:
        st.components.v1.html(html_str, height=900, scrolling=True)

    st.markdown("##### Download")
    is_admin = user.get("role") == "admin"
    cols = st.columns(2) if is_admin else st.columns(1)
    cols[0].download_button(
        "Download PNG", data=png_bytes, file_name=f"{file_stub}.png",
        mime="image/png", use_container_width=True,
    )
    if is_admin:
        cols[1].download_button(
            "Download HTML", data=html_str.encode("utf-8"), file_name=f"{file_stub}.html",
            mime="text/html", use_container_width=True,
        )


# ------------------------------------------------------------ admin panel --
def render_admin_panel():
    st.markdown("### ⚙️ Admin panel")
    tab_users, tab_units, tab_backup = st.tabs(["Users", "Units", "Backup & restore"])

    with tab_units:
        st.markdown("##### Units")
        units = store.load_units()
        st.table(pd.DataFrame({"Unit": units}) if units else pd.DataFrame({"Unit": []}))
        with st.form("add_unit_form", clear_on_submit=True):
            new_unit = st.text_input("New unit code (e.g. AM-14)")
            if st.form_submit_button("Add unit"):
                if new_unit.strip():
                    store.add_unit(new_unit.strip())
                    st.success(f"Added unit {new_unit.strip()}.")
                    st.rerun()
        if units:
            with st.form("remove_unit_form"):
                to_remove = st.selectbox("Remove a unit", units)
                if st.form_submit_button("Remove unit", type="secondary"):
                    store.remove_unit(to_remove)
                    st.warning(f"Removed unit {to_remove}.")
                    st.rerun()

    with tab_users:
        st.markdown("##### Existing users")
        users = store.list_users()
        rows = [
            {"Username": uname, "Full name": u.get("full_name", ""), "Role": u.get("role", ""),
             "Units": ", ".join(u.get("units", [])) or ("ALL" if u.get("role") == "admin" else ""),
             "Active": u.get("active", True)}
            for uname, u in users.items()
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("##### Create a new user")
        all_units = store.load_units()
        with st.form("create_user_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            new_username = c1.text_input("Username")
            new_full_name = c2.text_input("Full name")
            c3, c4 = st.columns(2)
            new_email = c3.text_input("Email")
            new_role = c4.selectbox("Role", ["user", "admin"])
            assigned_units = st.multiselect("Assign unit(s)", all_units)
            new_password = st.text_input("Temporary password (leave blank to auto-generate)")
            if st.form_submit_button("Create user", type="primary"):
                if not new_username.strip():
                    st.error("Username is required.")
                elif store.get_user(new_username.strip()):
                    st.error("That username already exists.")
                else:
                    pw = new_password.strip() or auth.generate_temp_password()
                    salt, pw_hash = auth.hash_password(pw)
                    store.upsert_user(new_username.strip(), {
                        "password_salt": salt, "password_hash": pw_hash,
                        "role": new_role, "full_name": new_full_name or new_username.strip(),
                        "email": new_email, "units": assigned_units, "active": True,
                        "created_at": store.now_iso(),
                    })
                    st.success(f"User '{new_username.strip()}' created. Temporary password: `{pw}`")
                    st.rerun()

        if users:
            st.markdown("##### Manage an existing user")
            editable = [u for u in users.keys()]
            with st.form("manage_user_form"):
                target = st.selectbox("Select user", editable)
                target_record = users.get(target, {})
                c1, c2 = st.columns(2)
                edit_role = c1.selectbox("Role", ["user", "admin"], index=["user", "admin"].index(target_record.get("role", "user")))
                edit_active = c2.checkbox("Active", value=target_record.get("active", True))
                edit_units = st.multiselect("Assigned unit(s)", all_units, default=[u for u in target_record.get("units", []) if u in all_units])
                reset_pw = st.text_input("Reset password (leave blank to keep current)")
                b1, b2 = st.columns(2)
                save_clicked = b1.form_submit_button("Save changes", type="primary")
                delete_clicked = b2.form_submit_button("Delete user", type="secondary")

            if save_clicked:
                record = dict(target_record)
                record["role"] = edit_role
                record["active"] = edit_active
                record["units"] = edit_units
                if reset_pw.strip():
                    salt, pw_hash = auth.hash_password(reset_pw.strip())
                    record["password_salt"] = salt
                    record["password_hash"] = pw_hash
                store.upsert_user(target, record)
                st.success(f"Updated '{target}'.")
                st.rerun()
            if delete_clicked:
                if target == st.session_state["user"]["username"]:
                    st.error("You cannot delete the account you are logged in as.")
                else:
                    store.delete_user(target)
                    st.warning(f"Deleted '{target}'.")
                    st.rerun()

    with tab_backup:
        st.markdown("##### Backup")
        st.caption(
            "Streamlit Community Cloud's storage is not guaranteed to survive a redeploy. "
            "Download a backup regularly, and re-import it after any redeploy."
        )
        import json
        bundle = store.export_all()
        st.download_button(
            "Download full backup (JSON)",
            data=json.dumps(bundle, indent=2).encode("utf-8"),
            file_name=f"icu_dashboard_backup_{date.today().isoformat()}.json",
            mime="application/json",
        )
        st.markdown("##### Restore")
        uploaded = st.file_uploader("Upload a backup JSON file to restore", type=["json"])
        if uploaded is not None:
            if st.button("Restore from this file", type="primary"):
                try:
                    data = json.loads(uploaded.read().decode("utf-8"))
                    store.import_all(data)
                    st.success("Restore complete. Please refresh the page.")
                except Exception as e:
                    st.error(f"Could not restore backup: {e}")


# ------------------------------------------------------------------- main --
def render_app():
    user = st.session_state["user"]
    with st.sidebar:
        st.markdown(f"**{COMPANY_NAME}**")
        st.caption(APP_TITLE)
        st.markdown("---")
        st.write(f"👤 **{user.get('full_name') or user['username']}**")
        st.caption(f"Role: {user.get('role', 'user').title()}")
        if user.get("role") != "admin":
            units = user.get("units", [])
            st.caption("Units: " + (", ".join(units) if units else "none assigned"))
        st.markdown("---")
        if st.button("Log out", use_container_width=True):
            del st.session_state["user"]
            st.rerun()

    st.markdown(f"## 📊 {APP_TITLE}")

    if user.get("role") == "admin":
        tabs = st.tabs(["📅 Monthly Dashboard", "🗓️ Weekly Dashboard", "⚙️ Admin Panel"])
        with tabs[0]:
            render_monthly_tab(user)
        with tabs[1]:
            render_weekly_tab(user)
        with tabs[2]:
            render_admin_panel()
    else:
        tabs = st.tabs(["📅 Monthly Dashboard", "🗓️ Weekly Dashboard"])
        with tabs[0]:
            render_monthly_tab(user)
        with tabs[1]:
            render_weekly_tab(user)


def main():
    inject_css()
    if not store.any_admin_exists():
        render_initial_setup()
        return
    if "user" not in st.session_state:
        render_login()
        return
    render_app()


if __name__ == "__main__":
    main()
