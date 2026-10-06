# Nexis Moodle — Unified Project

## Architecture

- `main.py` — Telegram/Moodle/archive/AI backend.
- `gpa5.py` — GPA5 study engine used by `main.py`.
- `web/` — Nexis Moodle web/PWA interface.
- The web interface does **not** bundle Moodle data, archive files, credentials, or GPA5 data.
- Web data must come from the backend API (`NEXIS_API_BASE_URL`) so the server remains the single source of truth.
- Telegram login uses the same Telegram identity as the bot: `NexisMBot`.

## Required web environment

Set:

`NEXIS_API_BASE_URL=<your running Nexis backend URL>`

Optional:

`VITE_TELEGRAM_BOT_USERNAME=NexisMBot`

## Important

`main.py` currently starts `web_api.start_web(...)`; keep the existing server-side `web_api` module with the backend deployment. It is intentionally not duplicated inside the web frontend.
