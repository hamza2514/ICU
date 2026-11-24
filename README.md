# ICU Dashboard Studio

Streamlit app for building the monthly and weekly ICU (Input vs Output) dashboards,
with login, an in-app admin panel, unit assignment, and PNG / HTML export.

## Deploy (no local setup needed)
1. Create a new GitHub repository and upload everything in this folder (keep the structure).
2. Go to https://share.streamlit.io -> **New app** -> pick the repo, branch `main`, main file `app.py`.
3. Open the deployed app. On first launch it shows **"Create admin account"** - fill it in.
   (The admin is created inside the app; there are no credentials in the code.)
4. Admin Panel -> **Units**: add your units (e.g. AM-04, AM-14).
5. Admin Panel -> **Users**: create users and assign their unit(s).

## Roles
- **Admin**: all units, create/edit/delete users, manage units, download **PNG and HTML**, backup/restore.
- **User**: only assigned units, download **PNG** only.

## How the numbers work
You enter only raw figures per period (Production, Rejection In/Out, Alteration In/Out).
Everything else is calculated: percentages, Confirmed Rejection = (Rejection In - Rejection Out) / Production,
and the monthly totals (sum of the weeks).

## IMPORTANT: data persistence
Users, units and saved dashboards are stored as JSON files in `data/`. Streamlit Community Cloud
does not guarantee disk storage survives a redeploy/reboot. Use **Admin Panel -> Backup & restore**
to download a backup regularly and re-upload it after a redeploy.
Sessions are per browser tab: refreshing the page requires logging in again.

## PNG vs HTML
PNG is rendered with matplotlib (no browser needed, reliable on Streamlit Cloud) using bundled
DejaVu fonts. The HTML download uses the original branded Google Fonts design.
