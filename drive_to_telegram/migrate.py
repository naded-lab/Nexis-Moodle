import asyncio
import hashlib
import os
import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from telethon import TelegramClient
from telethon.errors import FloodWaitError

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "migration.db"
DOWNLOAD_DIR = BASE / "downloads"
LINKS_FILE = BASE / "links.txt"

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ.get("TG_SESSION", str(BASE / "telegram_migration"))
DESTINATION = os.environ["TG_DESTINATION"]

MAX_RETRIES = int(os.environ.get("MIGRATION_RETRIES", "3"))
CHUNK_SIZE = 8 * 1024 * 1024

# Migration size window in MB.
# Example: MIN=0, MAX=10 processes files up to 10 MB.
MIGRATION_MIN_MB = float(os.environ.get("MIGRATION_MIN_MB", "0"))
MIGRATION_MAX_MB = float(os.environ.get("MIGRATION_MAX_MB", "10"))

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

db = sqlite3.connect(DB_PATH)
db.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    file_id TEXT,
    filename TEXT,
    size INTEGER,
    sha256 TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    telegram_message_id INTEGER,
    error TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
)
""")
db.commit()


def extract_file_id(url):
    m = re.search(r"/file/d/([-\w]+)", url)
    if m:
        return m.group(1)

    m = re.search(r"[?&]id=([-\w]+)", url)
    if m:
        return m.group(1)

    return None


def load_links():
    if not LINKS_FILE.exists():
        raise SystemExit(f"Missing {LINKS_FILE}")

    links = []
    seen = set()

    for line in LINKS_FILE.read_text(encoding="utf-8").splitlines():
        url = line.strip()
        if not url or url.startswith("#"):
            continue

        if not url.startswith(("http://", "https://")):
            continue

        if url in seen:
            continue

        seen.add(url)
        links.append(url)

    return links


def register_links(links):
    now = int(time.time())

    for url in links:
        fid = extract_file_id(url)

        db.execute("""
        INSERT OR IGNORE INTO files
        (url, file_id, status, created_at, updated_at)
        VALUES (?, ?, 'pending', ?, ?)
        """, (url, fid, now, now))

    db.commit()


def download_file(file_id, url, item_id):
    download_url = (
        "https://drive.google.com/uc"
        f"?export=download&id={file_id}"
    )

    temp = DOWNLOAD_DIR / f"{item_id}.part"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    with requests.get(
        download_url,
        headers=headers,
        stream=True,
        allow_redirects=True,
        timeout=(30, 120),
    ) as r:
        r.raise_for_status()

        content_type = r.headers.get("content-type", "")

        if "text/html" in content_type.lower():
            raise RuntimeError(
                "Google Drive returned HTML instead of the file. "
                "The shared file may require additional permission."
            )

        total = int(r.headers.get("content-length") or 0)
        written = 0
        sha = hashlib.sha256()

        with open(temp, "wb") as f:
            for chunk in r.iter_content(CHUNK_SIZE):
                if not chunk:
                    continue

                f.write(chunk)
                sha.update(chunk)
                written += len(chunk)

        if written == 0:
            raise RuntimeError("Downloaded file is empty.")

    digest = sha.hexdigest()

    filename = None

    cd = r.headers.get("content-disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd, re.I)
    if m:
        filename = m.group(1).strip().strip('"')

    if not filename:
        filename = f"drive_{file_id}"

    safe = re.sub(r'[\\/:*?"<>|]+', "_", filename).strip()
    if not safe:
        safe = f"drive_{file_id}"

    final = DOWNLOAD_DIR / safe

    if final.exists():
        final = DOWNLOAD_DIR / f"{item_id}_{safe}"

    temp.rename(final)

    return final, written, digest, total


async def migrate():
    links = load_links()
    register_links(links)

    client = TelegramClient(SESSION, API_ID, API_HASH)

    await client.start()

    entity = await client.get_entity(DESTINATION)

    pending = db.execute("""
        SELECT id, url, file_id, attempts
        FROM files
        WHERE status NOT IN ('done', 'skipped')
        ORDER BY id
    """).fetchall()

    print(f"Total links: {len(links)}")
    print(f"Pending: {len(pending)}")

    for item_id, url, file_id, attempts in pending:
        print(f"\n[{item_id}] {url}")

        if not file_id:
            db.execute(
                "UPDATE files SET status='failed', error=?, updated_at=? WHERE id=?",
                ("Invalid Google Drive URL", int(time.time()), item_id),
            )
            db.commit()
            print("SKIP: invalid Drive URL")
            continue

        success = False

        for attempt in range(attempts + 1, MAX_RETRIES + 1):
            try:
                db.execute(
                    "UPDATE files SET status='downloading', attempts=?, updated_at=? WHERE id=?",
                    (attempt, int(time.time()), item_id),
                )
                db.commit()

                path, size, digest, expected = download_file(
                    file_id, url, item_id
                )

                print(f"Downloaded: {size / 1024 / 1024:.2f} MB")
                print(f"SHA256: {digest}")

                db.execute("""
                    UPDATE files
                    SET filename=?, size=?, sha256=?, status='uploading',
                        updated_at=?, error=NULL
                    WHERE id=?
                """, (
                    path.name,
                    size,
                    digest,
                    int(time.time()),
                    item_id,
                ))
                db.commit()

                upload_started = time.monotonic()
                last_print = [0.0]

                def upload_progress(current, total):
                    now = time.monotonic()
                    if now - last_print[0] < 1.0 and current < total:
                        return
                    last_print[0] = now
                    elapsed = max(now - upload_started, 0.001)
                    speed = current / elapsed
                    percent = (current / total * 100) if total else 0
                    print(
                        f"UPLOAD: {percent:6.2f}% | "
                        f"{current / 1024 / 1024:.2f}/{total / 1024 / 1024:.2f} MB | "
                        f"{speed / 1024 / 1024:.2f} MB/s",
                        flush=True,
                    )

                message = await client.send_file(
                    entity,
                    str(path),
                    caption=path.name,
                    supports_streaming=True,
                    progress_callback=upload_progress,
                )

                db.execute("""
                    UPDATE files
                    SET status='done',
                        telegram_message_id=?,
                        updated_at=?,
                        error=NULL
                    WHERE id=?
                """, (
                    message.id,
                    int(time.time()),
                    item_id,
                ))
                db.commit()

                try:
                    path.unlink()
                except OSError:
                    pass

                print(f"UPLOADED: Telegram message {message.id}")
                success = True
                break

            except FloodWaitError as e:
                print(f"Telegram rate limit: waiting {e.seconds}s")
                await asyncio.sleep(e.seconds)

            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                print(f"FAILED attempt {attempt}: {error}")

                db.execute(
                    "UPDATE files SET status='retry', error=?, updated_at=? WHERE id=?",
                    (error[:1000], int(time.time()), item_id),
                )
                db.commit()

                if attempt < MAX_RETRIES:
                    await asyncio.sleep(min(30 * attempt, 120))

        if not success:
            db.execute(
                "UPDATE files SET status='failed', updated_at=? WHERE id=?",
                (int(time.time()), item_id),
            )
            db.commit()

    await client.disconnect()

    stats = db.execute("""
        SELECT status, COUNT(*)
        FROM files
        GROUP BY status
        ORDER BY status
    """).fetchall()

    print("\n=== MIGRATION SUMMARY ===")
    for status, count in stats:
        print(f"{status}: {count}")


if __name__ == "__main__":
    asyncio.run(migrate())
