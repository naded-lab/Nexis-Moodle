"""
سكريبت لتسجيل الدخول لموودل جامعة الأقصى، والدخول على كل مقرر،
واستخراج الاختبارات/الواجبات (Quiz) مع تواريخ الفتح والإغلاق.

طريقة الاستخدام:
1. ثبّت المكتبات:
   pip install requests beautifulsoup4

2. عدّل USERNAME و PASSWORD تحت (أو خليهم كـ environment variables، أأمن).

3. شغّل:
   python check_assignments.py

أمان: لا ترفع هذا الملف بعد تعبئة كلمة السر لأي مكان عام.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://moodle.alaqsa.edu.ps"
LOGIN_URL = f"{BASE_URL}/login/index.php"
COURSES_URL = f"{BASE_URL}/my/courses.php"

USERNAME = os.environ.get("MOODLE_USER", "1320250649")
PASSWORD = os.environ.get("MOODLE_PASS", "N10adid20")

# كم يوم قدام نعتبره "قريب" للواجبات (يعني لسا يستاهل تنبيه)
ASSIGNMENT_DAYS_AHEAD = 3

# كل كم يوم نفحص المحاضرات الجديدة (أسبوعي = 7)
LECTURE_CHECK_INTERVAL_DAYS = 7

STATE_FILE = "state.json"

# تلغرام (اختياري) — لو تركتهم فاضيين، السكريبت رح يطبع بالترمينال بس
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

OPEN_CLOSE_RE = re.compile(
    r"مفتوح\s*:\s*(.+?\d{1,2}:\d{2}\s*[AP]M)\s*مغلق\s*:\s*(.+?\d{1,2}:\d{2}\s*[AP]M)",
    re.IGNORECASE,
)

# الواجبات (mod_assign) بتستخدم تسميات تختلف عن الاختبارات:
# "فتحت:" (تاريخ الفتح) و "تستحق:" (تاريخ التسليم النهائي)
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


def parse_arabic_datetime(text: str):
    """يحاول يحول تاريخ عربي مكتوب (مثل 'الأربعاء، 29 يوليو 2026، 9:00 AM')
    إلى datetime. يرجع None إذا فشل."""
    match = DATE_RE.search(text)
    if not match:
        return None
    day, month_name, year, hour, minute, meridiem = match.groups()
    month = ARABIC_MONTHS.get(month_name)
    if not month:
        return None
    hour = int(hour)
    if meridiem.upper() == "PM" and hour != 12:
        hour += 12
    if meridiem.upper() == "AM" and hour == 12:
        hour = 0
    try:
        return datetime(int(year), month, int(day), hour, int(minute))
    except ValueError:
        return None


MONTH_NAMES_DISPLAY = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}


def short_date(text: str) -> str:
    """يشيل الوقت (9:00 AM) ويرجع بس اليوم والتاريخ، مثل 'الأربعاء 29 يوليو 2026'."""
    d = parse_arabic_datetime(text)
    if not d:
        return text.strip()
    weekday_ar = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    return f"{weekday_ar[d.weekday()]} {d.day} {MONTH_NAMES_DISPLAY.get(d.month, d.month)} {d.year}"


def get_login_token(session: requests.Session) -> str:
    resp = session.get(LOGIN_URL, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    token_input = soup.find("input", {"name": "logintoken"})
    if not token_input:
        raise RuntimeError("ما لقيت logintoken بصفحة تسجيل الدخول.")
    return token_input.get("value", "")


def login(session: requests.Session) -> None:
    token = get_login_token(session)
    payload = {"username": USERNAME, "password": PASSWORD, "logintoken": token}
    resp = session.post(LOGIN_URL, data=payload, timeout=20)
    resp.raise_for_status()
    if "login/index.php" in resp.url:
        raise RuntimeError("فشل تسجيل الدخول — تأكد من اسم المستخدم وكلمة المرور.")


def get_sesskey(html: str) -> str:
    match = re.search(r'"sesskey"\s*:\s*"([a-zA-Z0-9]+)"', html)
    if not match:
        raise RuntimeError("ما لقيت sesskey بالصفحة.")
    return match.group(1)


def get_courses(session: requests.Session):
    """يجيب لستة الكورسات عن طريق نفس طلب AJAX يلي المتصفح بيستخدمه."""
    resp = session.get(COURSES_URL, timeout=20)
    resp.raise_for_status()

    with open("debug_courses.html", "w", encoding="utf-8") as f:
        f.write(resp.text)

    sesskey = get_sesskey(resp.text)

    ajax_url = f"{BASE_URL}/lib/ajax/service.php"
    payload = [
        {
            "index": 0,
            "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
            "args": {
                "offset": 0,
                "limit": 0,
                "classification": "all",
                "sort": "fullname",
            },
        }
    ]

    ajax_resp = session.post(
        ajax_url,
        params={"sesskey": sesskey, "info": "core_course_get_enrolled_courses_by_timeline_classification"},
        json=payload,
        timeout=20,
    )
    ajax_resp.raise_for_status()

    with open("debug_ajax.json", "w", encoding="utf-8") as f:
        f.write(ajax_resp.text)

    data = ajax_resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"خطأ من موودل: {data.get('exception', {}).get('message')}")

    courses_data = data[0]["data"]["courses"]

    courses = []
    for c in courses_data:
        name = c.get("fullname", "بدون اسم")
        course_id = c.get("id")
        url = f"{BASE_URL}/course/view.php?id={course_id}"
        courses.append((name, url))

    if not courses:
        print("[تشخيص] رد الـ AJAX الكامل محفوظ بملف debug_ajax.json")

    return courses


def extract_link(act) -> str:
    """يجيب أول رابط فعلي (view.php) داخل عنصر النشاط."""
    link = act.select_one("a[href*='view.php']")
    if not link or not link.get("href"):
        return ""
    href = link["href"]
    if href.startswith("http"):
        return href
    return f"{BASE_URL}{href}"


def get_activities_for_course(session: requests.Session, course_url: str):
    """يفتح صفحة المقرر ويرجع (اختبارات، واجبات، محاضرات/محتوى)."""
    resp = session.get(course_url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    exams = []       # (name, open_date, close_date, link)
    assignments = []  # (name, open_date, due_date, link)
    materials = []    # (name, link)
    seen = set()

    # الاختبارات (مفتوح/مغلق)
    for act in soup.select("li.modtype_quiz"):
        text = act.get_text(" ", strip=True)
        match = OPEN_CLOSE_RE.search(text)
        if not match:
            continue

        name_el = act.select_one(".instancename")
        if name_el:
            for extra in name_el.select(".accesshide"):
                extra.extract()
            name = name_el.get_text(strip=True)
        else:
            name = "نشاط غير معروف"
        name = re.sub(r"\s+", " ", name).strip()

        open_date = match.group(1).strip()
        close_date = match.group(2).strip()
        link = extract_link(act)

        signature = (name, open_date, close_date)
        if signature in seen:
            continue
        seen.add(signature)
        exams.append((name, open_date, close_date, link))

    # الواجبات (فتحت/تستحق)
    for act in soup.select("li.modtype_assign"):
        text = act.get_text(" ", strip=True)
        match = ASSIGN_DATE_RE.search(text)
        if not match:
            continue

        name_el = act.select_one(".instancename")
        if name_el:
            for extra in name_el.select(".accesshide"):
                extra.extract()
            name = name_el.get_text(strip=True)
        else:
            name = "نشاط غير معروف"
        name = re.sub(r"\s+", " ", name).strip()

        open_date = match.group(1).strip()
        due_date = match.group(2).strip()
        link = extract_link(act)

        signature = (name, open_date, due_date)
        if signature in seen:
            continue
        seen.add(signature)
        assignments.append((name, open_date, due_date, link))

    # محتوى المحاضرات (ملفات، مجلدات، صفحات، روابط)
    material_selectors = "li.modtype_resource, li.modtype_folder, li.modtype_page, li.modtype_url"
    for act in soup.select(material_selectors):
        name_el = act.select_one(".instancename")
        if not name_el:
            continue
        for extra in name_el.select(".accesshide"):
            extra.extract()
        name = re.sub(r"\s+", " ", name_el.get_text(strip=True)).strip()
        if not name:
            continue

        link = extract_link(act)
        materials.append((name, link))

    return exams, assignments, materials


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"seen_material_ids": [], "last_lecture_check": None}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"seen_material_ids": [], "last_lecture_check": None}


def save_state(state) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_telegram_message(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=20,
        )
    except requests.RequestException as exc:
        print(f"[تحذير] فشل إرسال رسالة تلغرام: {exc}", file=sys.stderr)


def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    print("جاري تسجيل الدخول...")
    login(session)
    print("تم تسجيل الدخول بنجاح.\n")

    courses = get_courses(session)
    if not courses:
        print("ما لقيت مقررات — تأكد إنك مسجل دخول صحيح.")
        return

    now = datetime.now()
    assignment_cutoff = now + timedelta(days=ASSIGNMENT_DAYS_AHEAD)

    state = load_state()
    seen_material_ids = set(state.get("seen_material_ids", []))
    last_check_str = state.get("last_lecture_check")
    last_check = datetime.fromisoformat(last_check_str) if last_check_str else None
    check_lectures_this_run = (
        last_check is None
        or (now - last_check) >= timedelta(days=LECTURE_CHECK_INTERVAL_DAYS)
    )

    exams_due = []       # (course, name, open_date, close_date, close_dt, status, link)
    assignments_due = []  # (course, name, open_date, due_date, due_dt, link)
    new_materials = []    # (course, name, link)
    all_material_links_this_run = set()

    for course_name, href in courses:
        exams, assignments, materials = get_activities_for_course(session, href)

        # الامتحانات: الأهم — نعرضها كلها دايمًا (مفتوحة أو لسا جاية)، أي وقت
        for name, open_date, close_date, link in exams:
            close_dt = parse_arabic_datetime(close_date)
            if close_dt and close_dt < now:
                continue  # خلص وقته، ما فيه فايدة نعرضه
            open_dt = parse_arabic_datetime(open_date)
            status = "لسا ما فتح" if (open_dt and open_dt > now) else "مفتوح الآن ✅"
            exams_due.append((course_name, name, open_date, close_date, close_dt, status, link))

        # الواجبات: بس يلي باقي عليها القليل المحدد
        for name, open_date, due_date, link in assignments:
            due_dt = parse_arabic_datetime(due_date)
            if due_dt and now <= due_dt <= assignment_cutoff:
                assignments_due.append((course_name, name, open_date, due_date, due_dt, link))

        # المحاضرات: نجمع كل رابط شفناه هلأ، ونشوف شو جديد
        for name, link in materials:
            key = link or name
            all_material_links_this_run.add(key)
            if check_lectures_this_run and key not in seen_material_ids:
                new_materials.append((course_name, name, link))

    exams_due.sort(key=lambda r: (r[5] != "مفتوح الآن ✅",))
    assignments_due.sort(key=lambda r: r[4])

    lines = []

    if exams_due:
        print("📝 امتحانات:")
        lines.append("📝 امتحانات:")
        for course_name, name, open_date, close_date, close_dt, status, link in exams_due:
            when = short_date(close_date)
            line = f"{course_name} | امتحان: {name} | {when}"
            print(line)
            if link:
                print(f"    🔗 {link}")
            lines.append(line + (f"\n🔗 {link}" if link else ""))
        print()
    else:
        print("📝 مافي امتحانات حاليًا أو جاية قريب.\n")

    if assignments_due:
        print(f"📌 واجبات مستحقة خلال {ASSIGNMENT_DAYS_AHEAD} أيام:")
        lines.append(f"\n📌 واجبات مستحقة خلال {ASSIGNMENT_DAYS_AHEAD} أيام:")
        for course_name, name, open_date, due_date, due_dt, link in assignments_due:
            line = f"{course_name} | واجب: {name} | من {short_date(open_date)} إلى {short_date(due_date)}"
            print(line)
            if link:
                print(f"    🔗 {link}")
            lines.append(line + (f"\n🔗 {link}" if link else ""))
        print()
    else:
        print(f"📌 مافي واجبات مستحقة خلال {ASSIGNMENT_DAYS_AHEAD} أيام.\n")

    if check_lectures_this_run:
        if new_materials:
            print("📚 محاضرات جديدة هذا الأسبوع:")
            lines.append("\n📚 محاضرات جديدة هذا الأسبوع:")
            for course_name, name, link in new_materials:
                line = f"{course_name} | محاضرة: {name} | {now.strftime('%Y-%m-%d')}"
                print(line)
                if link:
                    print(f"    🔗 {link}")
                lines.append(line + (f"\n🔗 {link}" if link else ""))
        else:
            print("📚 ما في محتوى جديد بالمحاضرات هذا الأسبوع.")
    else:
        days_since = (now - last_check).days if last_check else 0
        print(
            f"📚 فحص المحاضرات أسبوعي — آخر فحص قبل {days_since} يوم."
        )

    if check_lectures_this_run:
        state["seen_material_ids"] = list(all_material_links_this_run)
        state["last_lecture_check"] = now.isoformat()
        save_state(state)

    if lines:
        send_telegram_message("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"حدث خطأ: {exc}", file=sys.stderr)
        sys.exit(1)
