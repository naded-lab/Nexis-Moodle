import asyncio
import hashlib
import os
import re
import sqlite3
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from cryptography.fernet import Fernet, InvalidToken
from telegram import Update
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

BASE_URL = "https://moodle.alaqsa.edu.ps"
LOGIN_URL = f"{BASE_URL}/login/index.php"
COURSES_URL = f"{BASE_URL}/my/courses.php"

DB_FILE = os.environ.get("NEXIS_DB_FILE", "nexis_moodle.db")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
MASTER_KEY = os.environ.get("NEXIS_MASTER_KEY", "")
ASSIGNMENT_DAYS_AHEAD = int(os.environ.get("ASSIGNMENT_DAYS_AHEAD", "3"))
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "60"))

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
if not MASTER_KEY:
    raise RuntimeError("NEXIS_MASTER_KEY is required")

try:
    CIPHER = Fernet(MASTER_KEY.encode())
except Exception as exc:
    raise RuntimeError("NEXIS_MASTER_KEY must be a valid Fernet key") from exc

USERNAME, PASSWORD = range(2)

OPEN_CLOSE_RE = re.compile(
    r"مفتوح\s*:\s*(.+?\d{1,2}:\d{2}\s*[AP]M)\s*مغلق\s*:\s*(.+?\d{1,2}:\d{2}\s*[AP]M)",
    re.IGNORECASE,
)
ASSIGN_DATE_RE = re.compile(
    r"فتحت\s*:\s*(.+?\d{1,2}:\d{2}\s*[AP]M)\s*تستحق\s*:\s*(.+?\d{1,2}:\d{2}\s*[AP]M)",
    re.IGNORECASE,
)
ARABIC_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4,
    "مايو": 5, "يونيو": 6, "يوليو": 7, "أغسطس": 8, "اغسطس": 8,
    "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
}
DATE_RE = re.compile(
    r"(\d{1,2})\s+(" + "|".join(ARABIC_MONTHS.keys()) + r")\s+(\d{4})،?\s*"
    r"(\d{1,2}):(\d{2})\s*(AM|PM)",
    re.IGNORECASE,
)
MONTH_NAMES_DISPLAY = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}

def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                moodle_username TEXT NOT NULL,
                password_encrypted TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_items (
                telegram_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_key TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                PRIMARY KEY (telegram_id, item_type, item_key)
            )
        """)

def save_user(telegram_id, username, password):
    encrypted = CIPHER.encrypt(password.encode()).decode()
    now = datetime.now().isoformat()
    with db() as conn:
        conn.execute("""
            INSERT INTO users (telegram_id, moodle_username, password_encrypted, enabled, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                moodle_username=excluded.moodle_username,
                password_encrypted=excluded.password_encrypted,
                enabled=1,
                updated_at=excluded.updated_at
        """, (telegram_id, username, encrypted, now, now))

def get_user(telegram_id):
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()

def get_password(row):
    try:
        return CIPHER.decrypt(row["password_encrypted"].encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("تعذر فك تشفير بيانات الدخول؛ تحقق من NEXIS_MASTER_KEY.") from exc

def delete_user(telegram_id):
    with db() as conn:
        conn.execute("DELETE FROM seen_items WHERE telegram_id=?", (telegram_id,))
        conn.execute("DELETE FROM users WHERE telegram_id=?", (telegram_id,))

def item_seen(telegram_id, item_type, item_key):
    with db() as conn:
        return conn.execute(
            "SELECT 1 FROM seen_items WHERE telegram_id=? AND item_type=? AND item_key=?",
            (telegram_id, item_type, item_key)
        ).fetchone() is not None

def mark_seen(telegram_id, item_type, item_key):
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_items VALUES (?, ?, ?, ?)",
            (telegram_id, item_type, item_key, datetime.now().isoformat())
        )

def parse_arabic_datetime(text):
    match = DATE_RE.search(text)
    if not match:
        return None
    day, month_name, year, hour, minute, meridiem = match.groups()
    month = ARABIC_MONTHS.get(month_name)
    hour = int(hour)
    if meridiem.upper() == "PM" and hour != 12:
        hour += 12
    if meridiem.upper() == "AM" and hour == 12:
        hour = 0
    try:
        return datetime(int(year), month, int(day), hour, int(minute))
    except (ValueError, TypeError):
        return None

def short_date(text):
    d = parse_arabic_datetime(text)
    if not d:
        return text.strip()
    weekday_ar = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    return f"{weekday_ar[d.weekday()]} {d.day} {MONTH_NAMES_DISPLAY[d.month]} {d.year}"

def get_login_token(session):
    resp = session.get(LOGIN_URL, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    token_input = soup.find("input", {"name": "logintoken"})
    if not token_input:
        raise RuntimeError("ما لقيت logintoken بصفحة تسجيل الدخول.")
    return token_input.get("value", "")

def login(session, username, password):
    token = get_login_token(session)
    resp = session.post(
        LOGIN_URL,
        data={"username": username, "password": password, "logintoken": token},
        timeout=20,
    )
    resp.raise_for_status()
    if "login/index.php" in resp.url:
        raise RuntimeError("فشل تسجيل الدخول — تأكد من اسم المستخدم وكلمة المرور.")

def get_sesskey(html):
    match = re.search(r'"sesskey"\s*:\s*"([a-zA-Z0-9]+)"', html)
    if not match:
        raise RuntimeError("ما لقيت sesskey بصفحة Moodle.")
    return match.group(1)

def get_courses(session):
    resp = session.get(COURSES_URL, timeout=20)
    resp.raise_for_status()
    sesskey = get_sesskey(resp.text)
    payload = [{
        "index": 0,
        "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
        "args": {"offset": 0, "limit": 0, "classification": "all", "sort": "fullname"},
    }]
    ajax_resp = session.post(
        f"{BASE_URL}/lib/ajax/service.php",
        params={"sesskey": sesskey, "info": "core_course_get_enrolled_courses_by_timeline_classification"},
        json=payload,
        timeout=20,
    )
    ajax_resp.raise_for_status()
    data = ajax_resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"خطأ من Moodle: {data.get('exception', {}).get('message')}")
    return [
        (c.get("fullname", "بدون اسم"), f"{BASE_URL}/course/view.php?id={c.get('id')}")
        for c in data[0]["data"]["courses"]
    ]

def extract_link(act):
    link = act.select_one("a[href*='view.php']")
    if not link or not link.get("href"):
        return ""
    href = link["href"]
    return href if href.startswith("http") else f"{BASE_URL}{href}"

def get_activities_for_course(session, course_url):
    resp = session.get(course_url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    exams, assignments, materials = [], [], []
    seen = set()

    for act in soup.select("li.modtype_quiz"):
        match = OPEN_CLOSE_RE.search(act.get_text(" ", strip=True))
        if not match:
            continue
        name_el = act.select_one(".instancename")
        if name_el:
            for extra in name_el.select(".accesshide"):
                extra.extract()
            name = re.sub(r"\s+", " ", name_el.get_text(strip=True)).strip()
        else:
            name = "نشاط غير معروف"
        open_date, close_date = match.group(1).strip(), match.group(2).strip()
        link = extract_link(act)
        sig = (name, open_date, close_date)
        if sig not in seen:
            seen.add(sig)
            exams.append((name, open_date, close_date, link))

    for act in soup.select("li.modtype_assign"):
        match = ASSIGN_DATE_RE.search(act.get_text(" ", strip=True))
        if not match:
            continue
        name_el = act.select_one(".instancename")
        if name_el:
            for extra in name_el.select(".accesshide"):
                extra.extract()
            name = re.sub(r"\s+", " ", name_el.get_text(strip=True)).strip()
        else:
            name = "نشاط غير معروف"
        open_date, due_date = match.group(1).strip(), match.group(2).strip()
        link = extract_link(act)
        sig = (name, open_date, due_date)
        if sig not in seen:
            seen.add(sig)
            assignments.append((name, open_date, due_date, link))

    for act in soup.select("li.modtype_resource, li.modtype_folder, li.modtype_page, li.modtype_url"):
        name_el = act.select_one(".instancename")
        if not name_el:
            continue
        for extra in name_el.select(".accesshide"):
            extra.extract()
        name = re.sub(r"\s+", " ", name_el.get_text(strip=True)).strip()
        if name:
            materials.append((name, extract_link(act)))

    return exams, assignments, materials

def run_check(telegram_id, only_new=False):
    row = get_user(telegram_id)
    if not row:
        raise RuntimeError("لا يوجد حساب Moodle مربوط.")
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Nexis Moodle Bot)"})
    login(session, row["moodle_username"], get_password(row))
    courses = get_courses(session)
    if not courses:
        return "لم أجد مقررات في حساب Moodle."

    now = datetime.now()
    cutoff = now + timedelta(days=ASSIGNMENT_DAYS_AHEAD)
    exams, assignments, materials = [], [], []

    for course_name, href in courses:
        ce, ca, cm = get_activities_for_course(session, href)
        for name, opened, closed, link in ce:
            close_dt = parse_arabic_datetime(closed)
            if close_dt and close_dt < now:
                continue
            open_dt = parse_arabic_datetime(opened)
            status = "لسا ما فتح" if open_dt and open_dt > now else "مفتوح الآن"
            exams.append((course_name, name, opened, closed, status, link))
        for name, opened, due, link in ca:
            due_dt = parse_arabic_datetime(due)
            if due_dt and now <= due_dt <= cutoff:
                assignments.append((course_name, name, opened, due, link))
        for name, link in cm:
            materials.append((course_name, name, link))

    sections, new_items = [], []

    for course, name, opened, closed, status, link in exams:
        key = hashlib.sha256(f"{course}|{name}|{opened}|{closed}".encode()).hexdigest()
        if not item_seen(telegram_id, "exam", key):
            new_items.append(("exam", key))
            if only_new:
                sections.append(f"📝 {course}\n{name}\n{status}\n{short_date(closed)}" + (f"\n🔗 {link}" if link else ""))

    for course, name, opened, due, link in assignments:
        key = hashlib.sha256(f"{course}|{name}|{opened}|{due}".encode()).hexdigest()
        if not item_seen(telegram_id, "assignment", key):
            new_items.append(("assignment", key))
            if only_new:
                sections.append(f"📌 {course}\n{name}\nالتسليم: {short_date(due)}" + (f"\n🔗 {link}" if link else ""))

    for course, name, link in materials:
        key = hashlib.sha256(f"{course}|{name}|{link}".encode()).hexdigest()
        if not item_seen(telegram_id, "material", key):
            new_items.append(("material", key))
            if only_new:
                sections.append(f"📚 {course}\n{name}" + (f"\n{link}" if link else ""))

    for item_type, key in new_items:
        mark_seen(telegram_id, item_type, key)

    if only_new:
        return "🔔 تحديثات Nexis Moodle:\n\n" + "\n\n".join(sections) if sections else "لا توجد تحديثات جديدة منذ آخر فحص."

    lines = []
    exams.sort(key=lambda x: x[4] != "مفتوح الآن")
    if exams:
        lines.append("📝 الامتحانات:")
        lines.extend(
            f"{course} | {name} | {status} | {short_date(closed)}" + (f"\n🔗 {link}" if link else "")
            for course, name, opened, closed, status, link in exams
        )
    else:
        lines.append("📝 لا توجد امتحانات حالية أو قادمة.")

    if assignments:
        assignments.sort(key=lambda x: parse_arabic_datetime(x[3]) or datetime.max)
        lines.append(f"📌 الواجبات خلال {ASSIGNMENT_DAYS_AHEAD} أيام:")
        lines.extend(
            f"{course} | {name} | إلى {short_date(due)}" + (f"\n🔗 {link}" if link else "")
            for course, name, opened, due, link in assignments
        )
    else:
        lines.append(f"📌 لا توجد واجبات مستحقة خلال {ASSIGNMENT_DAYS_AHEAD} أيام.")
    return "\n\n".join(lines)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 أهلاً بك في Nexis Moodle.\n\n"
        "استخدم /login لربط حساب Moodle، ثم /check للفحص الآن.\n"
        "/status للحالة و /logout لحذف الحساب."
    )

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("تسجيل الدخول متاح في المحادثة الخاصة مع البوت فقط.")
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text("أرسل اسم مستخدم Moodle:")
    return USERNAME

async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["moodle_username"] = update.message.text.strip()
    await update.message.reply_text("أرسل كلمة مرور Moodle. سيتم حذف رسالة كلمة المرور بعد استلامها.")
    return PASSWORD

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    try:
        await update.message.delete()
    except Exception:
        pass
    username = context.user_data.pop("moodle_username", "")
    if not username or not password:
        await update.effective_chat.send_message("بيانات الدخول غير مكتملة. أعد المحاولة عبر /login.")
        return ConversationHandler.END

    await update.effective_chat.send_message("جاري اختبار تسجيل الدخول إلى Moodle...")
    try:
        def test():
            s = requests.Session()
            s.headers.update({"User-Agent": "Mozilla/5.0 (Nexis Moodle Bot)"})
            login(s, username, password)
            get_courses(s)
        await asyncio.to_thread(test)
        save_user(update.effective_user.id, username, password)
        await update.effective_chat.send_message("تم ربط حساب Moodle بنجاح. استخدم /check للفحص الآن.")
    except Exception as exc:
        await update.effective_chat.send_message(f"فشل تسجيل الدخول: {str(exc)}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("تم إلغاء تسجيل الدخول.")
    return ConversationHandler.END

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not get_user(update.effective_user.id):
        await update.message.reply_text("اربط حساب Moodle أولاً عبر /login.")
        return
    await update.message.reply_text("جاري فحص Moodle...")
    try:
        await update.message.reply_text(await asyncio.to_thread(run_check, update.effective_user.id, False))
    except Exception as exc:
        await update.message.reply_text(f"فشل الفحص: {str(exc)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = get_user(update.effective_user.id)
    if not row:
        await update.message.reply_text("لا يوجد حساب Moodle مربوط.")
        return
    await update.message.reply_text(
        f"حساب Moodle: {row['moodle_username']}\n"
        f"المراقبة: {'مفعّلة' if row['enabled'] else 'متوقفة'}\n"
        f"الفحص التلقائي: كل {CHECK_INTERVAL_MINUTES} دقيقة."
    )

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delete_user(update.effective_user.id)
    await update.message.reply_text("تم حذف حساب Moodle والبيانات المشفرة المرتبطة به.")

async def monitor_job(context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        users = conn.execute("SELECT telegram_id FROM users WHERE enabled=1").fetchall()
    for row in users:
        try:
            result = await asyncio.to_thread(run_check, row["telegram_id"], True)
            if not result.startswith("لا توجد تحديثات"):
                await context.bot.send_message(chat_id=row["telegram_id"], text=result)
        except Exception as exc:
            await context.bot.send_message(chat_id=row["telegram_id"], text=f"⚠️ تعذر فحص Moodle تلقائيًا: {str(exc)}")

def main():
    init_db()
    request = HTTPXRequest(connect_timeout=30, read_timeout=30, write_timeout=30, pool_timeout=30, http_version="1.1"); app = Application.builder().token(BOT_TOKEN).request(request).build()

    login_conv = ConversationHandler(
        entry_points=[CommandHandler("login", login_start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_chat=True,
        per_user=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(login_conv)
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("logout", logout))

    if app.job_queue is None:
        raise RuntimeError("JobQueue غير متاح. ثبّت python-telegram-bot[job-queue].")
    app.job_queue.run_repeating(monitor_job, interval=CHECK_INTERVAL_MINUTES * 60, first=30)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
