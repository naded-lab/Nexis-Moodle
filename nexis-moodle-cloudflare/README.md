# Nexis Moodle — Cloudflare Worker

This is the webhook/D1 version of Nexis-Moodle. It keeps the Moodle scraping/parsing behavior, replaces Telegram polling with a Telegram webhook, replaces SQLite with Cloudflare D1, and replaces the hourly python-telegram-bot JobQueue with a Cloudflare Cron Trigger.

Required Cloudflare secrets:
- `TELEGRAM_BOT_TOKEN`
- `NEXIS_MASTER_KEY`
- `WEBHOOK_SECRET`

Required GitHub Actions secrets:
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

Do not commit secret values.
