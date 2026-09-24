import hashlib
import json
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from cryptography.fernet import Fernet, InvalidToken
from workers import WorkerEntrypoint, Response, fetch

BASE_URL = "https://moodle.alaqsa.edu.ps"
LOGIN_URL = f"{BASE_URL}/login/index.php"
COURSES_URL = f"{BASE_URL}/my/courses.php"

OPEN_CLOSE_RE = re.compile(r"مفتوح\s*:\s*(.+?\d{1,2}:\d{2}\s*[AP]M)\s*مغلق\s*:\s*(.+?\d{1,2}:\d{2}\s*[AP]M)", re.IGNORECASE)
ASSIGN_DATE_RE = re.compile(r"فتحت\s*:\s*(.+?\d{1,2}:\d{2}\s*[AP]M)\s*تستحق\s*:\s*(.+?\d{1,2}:\d{2}\s*[AP]M)", re.IGNORECASE)
ARABIC_MONTHS = {"يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4, "مايو": 5, "يونيو": 6, "يوليو": 7, "أغسطس": 8, "اغسطس": 8, "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12}
DATE_RE = re.compile(r"(\d{1,2})\s+(" + "|".join(ARABIC_MONTHS.keys()) + r")\s+(\d{4})،?\s*(\d{1,2}):(\d{2})\s*(AM|PM)", re.IGNORECASE)
MONTH_NAMES_DISPLAY = {1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}


def env_value(env, name, default=""):
    value = getattr(env, name, None)
    return value if value not in (None, "") else default


def cipher(env):
    key = env_value(env, "NEXIS_MASTER_KEY")
    if not key:
        raise RuntimeError("NEXIS_MASTER_KEY is required")
    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise RuntimeError("NEXIS_MASTER_KEY must be a valid Fernet key") from exc


def row_dict(row):
    return dict(row) if row else None


async def db_first(env, sql, *args):
    return row_dict(await env.DB.prepare(sql).bind(*args).first())


async def db_run(env, sql, *args):
    return await env.DB.prepare(sql).bind(*args).run()


async def save_user(env, telegram_id, username, password):
    encrypted = cipher(env).encrypt(password.encode()).decode()
    now = datetime.utcnow().isoformat()
    await db_run(env, """INSERT INTO users (telegram_id,moodle_username,password_encrypted,enabled,created_at,updated_at) VALUES (?,?,?,1,?,?) ON CONFLICT(telegram_id) DO UPDATE SET moodle_username=excluded.moodle_username,password_encrypted=excluded.password_encrypted,enabled=1,updated_at=excluded.updated_at""", telegram_id, username, encrypted, now, now)


async def get_user(env, telegram_id):
    return await db_first(env, "SELECT * FROM users WHERE telegram_id=?", telegram_id)


def get_password(env, row):
    try:
        return cipher(env).decrypt(row["password_encrypted"].encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("تعذر فك تشفير بيانات الدخول؛ تحقق من NEXIS_MASTER_KEY.") from exc


async def delete_user(env, telegram_id):
    await db_run(env, "DELETE FROM seen_items WHERE telegram_id=?", telegram_id)
    await db_run(env, "DELETE FROM users WHERE telegram_id=?", telegram_id)
    await db_run(env, "DELETE FROM pending_logins WHERE telegram_id=?", telegram_id)


async def item_seen(env, telegram_id, item_type, item_key):
    return await db_first(env, "SELECT 1 AS ok FROM seen_items WHERE telegram_id=? AND item_type=? AND item_key=?", telegram_id, item_type, item_key) is not None


async def mark_seen(env, telegram_id, item_type, item_key):
    await db_run(env, "INSERT OR IGNORE INTO seen_items VALUES (?,?,?,?)", telegram_id, item_type, item_key, datetime.utcnow().isoformat())


async def set_pending(env, telegram_id, state, username=None):
    await db_run(env, """INSERT INTO pending_logins(telegram_id,state,moodle_username,updated_at) VALUES(?,?,?,?) ON CONFLICT(telegram_id) DO UPDATE SET state=excluded.state,moodle_username=excluded.moodle_username,updated_at=excluded.updated_at""", telegram_id, state, username, datetime.utcnow().isoformat())


async def get_pending(env, telegram_id):
    return await db_first(env, "SELECT * FROM pending_logins WHERE telegram_id=?", telegram_id)


async def clear_pending(env, telegram_id):
    await db_run(env, "DELETE FROM pending_logins WHERE telegram_id=?", telegram_id)


def parse_arabic_datetime(text):
    match = DATE_RE.search(text)
    if not match:
        return None
    day, month_name, year, hour, minute, meridiem = match.groups()
    hour = int(hour)
    if meridiem.upper() == "PM" and hour != 12:
        hour += 12
    if meridiem.upper() == "AM" and hour == 12:
        hour = 0
    try:
        return datetime(int(year), ARABIC_MONTHS.get(month_name), int(day), hour, int(minute))
    except (ValueError, TypeError):
        return None


def short_date(text):
    d = parse_arabic_datetime(text)
    if not d:
        return text.strip()
    weekday_ar = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    return f"{weekday_ar[d.weekday()]} {d.day} {MONTH_NAMES_DISPLAY[d.month]} {d.year}"


class MoodleSession:
    def __init__(self):
        self.cookies = {}
        self.user_agent = "Mozilla/5.0 (Nexis Moodle Bot)"

    def cookie_header(self):
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())

    def update_cookies(self, response):
        try:
            values = response.headers.getAll("set-cookie")
        except Exception:
            value = response.headers.get("set-cookie")
            values = [value] if value else []
        for raw in values or []:
            first = raw.split(";", 1)[0]
            if "=" in first:
                key, value = first.split("=", 1)
                self.cookies[key.strip()] = value.strip()

    async def request(self, method, url, form=None, json_body=None, headers=None, max_redirects=5):
        current_url, current_method = url, method
        current_form, current_json = form, json_body
        for _ in range(max_redirects + 1):
            req_headers = {"User-Agent": self.user_agent}
            if self.cookies:
                req_headers["Cookie"] = self.cookie_header()
            if headers:
                req_headers.update(headers)
            options = {"method": current_method, "headers": req_headers, "redirect": "manual"}
            if current_form is not None:
                options["body"] = urlencode(current_form)
                req_headers["Content-Type"] = "application/x-www-form-urlencoded"
            elif current_json is not None:
                options["body"] = json.dumps(current_json)
                req_headers["Content-Type"] = "application/json"
            response = await fetch(current_url, options)
            self.update_cookies(response)
            status = int(response.status)
            if status in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    break
                current_url = BASE_URL + location if location.startswith("/") else location
                if status == 303 or (status in (301, 302) and current_method == "POST"):
                    current_method, current_form, current_json = "GET", None, None
                continue
            return response
        return response


async def get_login_token(session):
    resp = await session.request("GET", LOGIN_URL)
    if int(resp.status) >= 400:
        raise RuntimeError(f"Moodle returned HTTP {resp.status}")
    soup = BeautifulSoup(await resp.text(), "html.parser")
    token_input = soup.find("input", {"name": "logintoken"})
    if not token_input:
        raise RuntimeError("ما لقيت logintoken بصفحة تسجيل الدخول.")
    return token_input.get("value", "")


async def login(session, username, password):
    token = await get_login_token(session)
    resp = await session.request("POST", LOGIN_URL, form={"username": username, "password": password, "logintoken": token})
    if int(resp.status) >= 400:
        raise RuntimeError(f"Moodle returned HTTP {resp.status}")
    if "login/index.php" in str(resp.url):
        raise RuntimeError("فشل تسجيل الدخول — تأكد من اسم المستخدم وكلمة المرور.")


def get_sesskey(html):
    match = re.search(r'"sesskey"\s*:\s*"([a-zA-Z0-9]+)"', html)
    if not match:
        raise RuntimeError("ما لقيت sesskey بصفحة Moodle.")
    return match.group(1)


async def get_courses(session):
    resp = await session.request("GET", COURSES_URL)
    if int(resp.status) >= 400:
        raise RuntimeError(f"Moodle returned HTTP {resp.status}")
    sesskey = get_sesskey(await resp.text())
    payload = [{"index": 0, "methodname": "core_course_get_enrolled_courses_by_timeline_classification", "args": {"offset": 0, "limit": 0, "classification": "all", "sort": "fullname"}}]
    ajax_resp = await session.request("POST", f"{BASE_URL}/lib/ajax/service.php?{urlencode({'sesskey': sesskey, 'info': 'core_course_get_enrolled_courses_by_timeline_classification'})}", json_body=payload)
    if int(ajax_resp.status) >= 400:
        raise RuntimeError(f"Moodle AJAX returned HTTP {ajax_resp.status}")
    data = await ajax_resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"خطأ من Moodle: {data.get('exception', {}).get('message')}")
    return [(c.get("fullname", "بدون اسم"), f"{BASE_URL}/course/view.php?id={c.get('id')}") for c in data[0]["data"]["courses"]]


def extract_link(act):
    link = act.select_one("a[href*='view.php']")
    if not link or not link.get("href"):
        return ""
    href = link["href"]
    return href if href.startswith("http") else f"{BASE_URL}{href}"


async def get_activities_for_course(session, course_url):
    resp = await session.request("GET", course_url)
    if int(resp.status) >= 400:
        raise RuntimeError(f"Moodle returned HTTP {resp.status}")
    soup = BeautifulSoup(await resp.text(), "html.parser")
    exams, assignments, materials, seen = [], [], [], set()
    for act in soup.select("li.modtype_quiz"):
        match = OPEN_CLOSE_RE.search(act.get_text(" ", strip=True))
        if not match: continue
        name_el = act.select_one(".instancename")
        if name_el:
            for extra in name_el.select(".accesshide"): extra.extract()
            name = re.sub(r"\s+", " ", name_el.get_text(strip=True)).strip()
        else: name = "نشاط غير معروف"
        opened, closed, link = match.group(1).strip(), match.group(2).strip(), extract_link(act)
        sig = (name, opened, closed)
        if sig not in seen: seen.add(sig); exams.append((name, opened, closed, link))
    for act in soup.select("li.modtype_assign"):
        match = ASSIGN_DATE_RE.search(act.get_text(" ", strip=True))
        if not match: continue
        name_el = act.select_one(".instancename")
        if name_el:
            for extra in name_el.select(".accesshide"): extra.extract()
            name = re.sub(r"\s+", " ", name_el.get_text(strip=True)).strip()
        else: name = "نشاط غير معروف"
        opened, due, link = match.group(1).strip(), match.group(2).strip(), extract_link(act)
        sig = (name, opened, due)
        if sig not in seen: seen.add(sig); assignments.append((name, opened, due, link))
    for act in soup.select("li.modtype_resource, li.modtype_folder, li.modtype_page, li.modtype_url"):
        name_el = act.select_one(".instancename")
        if not name_el: continue
        for extra in name_el.select(".accesshide"): extra.extract()
        name = re.sub(r"\s+", " ", name_el.get_text(strip=True)).strip()
        if name: materials.append((name, extract_link(act)))
    return exams, assignments, materials


async def run_check(env, telegram_id, only_new=False):
    row = await get_user(env, telegram_id)
    if not row: raise RuntimeError("لا يوجد حساب Moodle مربوط.")
    session = MoodleSession()
    await login(session, row["moodle_username"], get_password(env, row))
    courses = await get_courses(session)
    if not courses: return "لم أجد مقررات في حساب Moodle."
    days_ahead = int(env_value(env, "ASSIGNMENT_DAYS_AHEAD", "3"))
    now, cutoff = datetime.utcnow(), datetime.utcnow() + timedelta(days=days_ahead)
    exams, assignments, materials = [], [], []
    for course_name, href in courses:
        ce, ca, cm = await get_activities_for_course(session, href)
        for name, opened, closed, link in ce:
            close_dt = parse_arabic_datetime(closed)
            if close_dt and close_dt < now: continue
            open_dt = parse_arabic_datetime(opened)
            exams.append((course_name, name, opened, closed, "لسا ما فتح" if open_dt and open_dt > now else "مفتوح الآن", link))
        for name, opened, due, link in ca:
            due_dt = parse_arabic_datetime(due)
            if due_dt and now <= due_dt <= cutoff: assignments.append((course_name, name, opened, due, link))
        materials.extend((course_name, name, link) for name, link in cm)
    sections, new_items = [], []
    for course, name, opened, closed, status, link in exams:
        key = hashlib.sha256(f"{course}|{name}|{opened}|{closed}".encode()).hexdigest()
        if not await item_seen(env, telegram_id, "exam", key):
            new_items.append(("exam", key))
            if only_new: sections.append(f"📝 {course}\n{name}\n{status}\n{short_date(closed)}" + (f"\n🔗 {link}" if link else ""))
    for course, name, opened, due, link in assignments:
        key = hashlib.sha256(f"{course}|{name}|{opened}|{due}".encode()).hexdigest()
        if not await item_seen(env, telegram_id, "assignment", key):
            new_items.append(("assignment", key))
            if only_new: sections.append(f"📌 {course}\n{name}\nالتسليم: {short_date(due)}" + (f"\n🔗 {link}" if link else ""))
    for course, name, link in materials:
        key = hashlib.sha256(f"{course}|{name}|{link}".encode()).hexdigest()
        if not await item_seen(env, telegram_id, "material", key):
            new_items.append(("material", key))
            if only_new: sections.append(f"📚 {course}\n{name}" + (f"\n{link}" if link else ""))
    for item_type, key in new_items: await mark_seen(env, telegram_id, item_type, key)
    if only_new: return "🔔 تحديثات Nexis Moodle:\n\n" + "\n\n".join(sections) if sections else "لا توجد تحديثات جديدة منذ آخر فحص."
    lines = []
    exams.sort(key=lambda x: x[4] != "مفتوح الآن")
    if exams:
        lines.append("📝 الامتحانات:")
        lines.extend(f"{course} | {name} | {status} | {short_date(closed)}" + (f"\n🔗 {link}" if link else "") for course, name, opened, closed, status, link in exams)
    else: lines.append("📝 لا توجد امتحانات حالية أو قادمة.")
    if assignments:
        assignments.sort(key=lambda x: parse_arabic_datetime(x[3]) or datetime.max)
        lines.append(f"📌 الواجبات خلال {days_ahead} أيام:")
        lines.extend(f"{course} | {name} | إلى {short_date(due)}" + (f"\n🔗 {link}" if link else "") for course, name, opened, due, link in assignments)
    else: lines.append(f"📌 لا توجد واجبات مستحقة خلال {days_ahead} أيام.")
    return "\n\n".join(lines)


async def telegram(env, method, payload):
    token = env_value(env, "TELEGRAM_BOT_TOKEN")
    if not token: raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    resp = await fetch(f"https://api.telegram.org/bot{token}/{method}", {"method": "POST", "headers": {"Content-Type": "application/json"}, "body": json.dumps(payload)})
    data = await resp.json()
    if not data.get("ok"): raise RuntimeError(data.get("description", f"Telegram API error: {method}"))
    return data.get("result")


async def send_message(env, chat_id, text): return await telegram(env, "sendMessage", {"chat_id": chat_id, "text": text})


async def delete_message(env, chat_id, message_id):
    try: await telegram(env, "deleteMessage", {"chat_id": chat_id, "message_id": message_id})
    except Exception: pass


async def handle_update(env, update):
    message = update.get("message")
    if not message or not message.get("chat"): return
    chat_id = message["chat"]["id"]
    user_id = message.get("from", {}).get("id", chat_id)
    text = (message.get("text") or "").strip()
    if text.startswith("/start"):
        await send_message(env, chat_id, "📚 أهلاً بك في Nexis Moodle.\n\nاستخدم /login لربط حساب Moodle، ثم /check للفحص الآن.\n/status للحالة و /logout لحذف الحساب.")
        return
    if text.startswith("/login"):
        if message["chat"].get("type") != "private":
            await send_message(env, chat_id, "تسجيل الدخول متاح في المحادثة الخاصة مع البوت فقط.")
            return
        await set_pending(env, user_id, "username")
        await send_message(env, chat_id, "أرسل اسم مستخدم Moodle:")
        return
    if text.startswith("/cancel"):
        await clear_pending(env, user_id); await send_message(env, chat_id, "تم إلغاء تسجيل الدخول."); return
    if text.startswith("/check"):
        if not await get_user(env, user_id): await send_message(env, chat_id, "اربط حساب Moodle أولاً عبر /login"); return
        await send_message(env, chat_id, "جاري فحص Moodle...")
        try: await send_message(env, chat_id, await run_check(env, user_id, False))
        except Exception as exc: await send_message(env, chat_id, f"فشل الفحص: {exc}")
        return
    if text.startswith("/status"):
        row = await get_user(env, user_id)
        if not row: await send_message(env, chat_id, "لا يوجد حساب Moodle مربوط."); return
        await send_message(env, chat_id, f"حساب Moodle: {row['moodle_username']}\nالمراقبة: {'مفعّلة' if row['enabled'] else 'متوقفة'}\nالفحص التلقائي: كل {env_value(env, 'CHECK_INTERVAL_MINUTES', '60')} دقيقة."); return
    if text.startswith("/logout"):
        await delete_user(env, user_id); await send_message(env, chat_id, "تم حذف حساب Moodle والبيانات المشفرة المرتبطة به."); return
    pending = await get_pending(env, user_id)
    if not pending or not text: return
    if pending["state"] == "username":
        await set_pending(env, user_id, "password", text); await send_message(env, chat_id, "أرسل كلمة مرور Moodle. سيتم حذف رسالة كلمة المرور بعد استلامها."); return
    if pending["state"] == "password":
        username = pending["moodle_username"] or ""
        await delete_message(env, chat_id, message.get("message_id")); await clear_pending(env, user_id)
        if not username: await send_message(env, chat_id, "بيانات الدخول غير مكتملة. أعد المحاولة عبر /login."); return
        await send_message(env, chat_id, "جاري اختبار تسجيل الدخول إلى Moodle...")
        try:
            session = MoodleSession(); await login(session, username, text); await get_courses(session); await save_user(env, user_id, username, text)
            await send_message(env, chat_id, "تم ربط حساب Moodle بنجاح. استخدم /check للفحص الآن.")
        except Exception as exc: await send_message(env, chat_id, f"فشل تسجيل الدخول: {exc}")


async def monitor_all(env):
    rows = await env.DB.prepare("SELECT telegram_id FROM users WHERE enabled=1").run()
    for row in rows.results:
        telegram_id = row["telegram_id"]
        try:
            result = await run_check(env, telegram_id, True)
            if not result.startswith("لا توجد تحديثات"): await send_message(env, telegram_id, result)
        except Exception as exc: await send_message(env, telegram_id, f"⚠️ تعذر فحص Moodle تلقائيًا: {exc}")


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if str(request.method).upper() != "POST": return Response("Nexis Moodle Worker")
        secret = env_value(self.env, "WEBHOOK_SECRET")
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret and supplied != secret: return Response("Unauthorized", status=401)
        try:
            await handle_update(self.env, await request.json())
            return Response("ok")
        except Exception as exc:
            print(f"Webhook error: {exc}")
            return Response("error", status=500)

    async def scheduled(self, controller, env, ctx):
        await monitor_all(env)
