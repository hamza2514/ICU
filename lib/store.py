"""Tiny JSON-file "database" for users, units, and saved dashboard records.

IMPORTANT (read this before relying on it in production):
Streamlit Community Cloud's filesystem is NOT guaranteed to persist across
a redeploy (a new git push) or a full app reboot/respin. Writes made while
the app is running (creating users, saving dashboards) DO persist across
normal restarts/wake-ups on the same container, but are NOT guaranteed to
survive a redeploy. Use Admin Panel -> "Backup & Restore" regularly to
export a full JSON backup, and re-import it after any redeploy that wipes
the data directory. For a bullet-proof setup long-term, point this file's
DATA_DIR at a mounted/external store (e.g. a small cloud database) instead
of local disk -- the rest of the app only talks to the functions below, so
that swap is isolated to this module.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
UNITS_FILE = os.path.join(DATA_DIR, "units.json")
MONTHLY_FILE = os.path.join(DATA_DIR, "dashboards_monthly.json")
WEEKLY_FILE = os.path.join(DATA_DIR, "dashboards_weekly.json")

_lock = threading.Lock()


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _read(path: str, default):
    _ensure_dir()
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write(path: str, data) -> None:
    _ensure_dir()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- users ----
def load_users() -> dict:
    return _read(USERS_FILE, {"users": {}})


def save_users(data: dict) -> None:
    with _lock:
        _write(USERS_FILE, data)


def any_admin_exists() -> bool:
    users = load_users().get("users", {})
    return any(u.get("role") == "admin" for u in users.values())


def get_user(username: str) -> dict | None:
    return load_users().get("users", {}).get(username)


def upsert_user(username: str, record: dict) -> None:
    data = load_users()
    data.setdefault("users", {})[username] = record
    save_users(data)


def delete_user(username: str) -> None:
    data = load_users()
    data.get("users", {}).pop(username, None)
    save_users(data)


def list_users() -> dict:
    return load_users().get("users", {})


# ---------------------------------------------------------------- units ----
def load_units() -> list[str]:
    return _read(UNITS_FILE, {"units": []}).get("units", [])


def save_units(units: list[str]) -> None:
    with _lock:
        _write(UNITS_FILE, {"units": sorted(set(units))})


def add_unit(unit: str) -> None:
    units = load_units()
    if unit not in units:
        units.append(unit)
        save_units(units)


def remove_unit(unit: str) -> None:
    units = load_units()
    if unit in units:
        units.remove(unit)
        save_units(units)


# ----------------------------------------------------------- dashboards ----
def load_monthly_records() -> dict:
    return _read(MONTHLY_FILE, {"records": {}})


def save_monthly_record(key: str, record: dict) -> None:
    data = load_monthly_records()
    record["saved_at"] = now_iso()
    data.setdefault("records", {})[key] = record
    with _lock:
        _write(MONTHLY_FILE, data)


def get_monthly_record(key: str) -> dict | None:
    return load_monthly_records().get("records", {}).get(key)


def load_weekly_records() -> dict:
    return _read(WEEKLY_FILE, {"records": {}})


def save_weekly_record(key: str, record: dict) -> None:
    data = load_weekly_records()
    record["saved_at"] = now_iso()
    data.setdefault("records", {})[key] = record
    with _lock:
        _write(WEEKLY_FILE, data)


def get_weekly_record(key: str) -> dict | None:
    return load_weekly_records().get("records", {}).get(key)


# -------------------------------------------------------- backup/restore ----
def export_all() -> dict:
    return {
        "exported_at": now_iso(),
        "users": load_users(),
        "units": {"units": load_units()},
        "dashboards_monthly": load_monthly_records(),
        "dashboards_weekly": load_weekly_records(),
    }


def import_all(bundle: dict) -> None:
    with _lock:
        if "users" in bundle:
            _write(USERS_FILE, bundle["users"])
        if "units" in bundle:
            _write(UNITS_FILE, bundle["units"])
        if "dashboards_monthly" in bundle:
            _write(MONTHLY_FILE, bundle["dashboards_monthly"])
        if "dashboards_weekly" in bundle:
            _write(WEEKLY_FILE, bundle["dashboards_weekly"])
