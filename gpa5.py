"""GPA5: برومبتات ونمط كل عملية دراسية (شرح / تلخيص / مفهوم / حل / ترجمة / أسئلة).
منقول من main.py كما هو بدون تغيير بالنص. main.py بيستورد منه، وما في هون أي اعتماد على main.py."""

import asyncio
import base64
import io
import random
import logging
import os
import re
import sqlite3
import threading
import time
import xml.etree.ElementTree as ET
import zipfile
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import Update
from telegram.error import RetryAfter
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler


# ===== هوية المساعد وقواعد الاستناد =====
AI_SYSTEM_PROMPT = (
    "أنت مساعد دراسي داخل بوت Nexis Moodle لطلاب جامعيين. بتساعد بكل ما يخص الدراسة: تلخيص وشرح المحتوى، "
    "توضيح المفاهيم، حل الأسئلة والمسائل وكتابة الأكواد بشكل تعليمي مع شرح الخطوات، والترجمة. "
    "إن كان الطلب بعيدًا تمامًا عن الدراسة والتعلم، اعتذر بلطف ووجّه الطالب لشي دراسي. "
    "أجب بالعربية الفصحى المبسطة ما لم يطلب الطالب لغة أخرى، وبنفس لغة الطالب إن كتب بالإنجليزية. "
    "ادخل في الجواب مباشرة: بدون مقدمات أو ترحيب أو تكرار للسؤال أو خاتمة. "
    "كن دقيقًا ومنظمًا ومختصرًا، وأطل فقط إذا كان الشرح يحتاجه فعلًا."
)

GROUNDING_RULES = (
    "\n\nلديك مقتطفات من مجموعات الطلاب. استخدمها فقط إذا كانت مرتبطة فعلًا بالسؤال، وابدأ الجزء المأخوذ منها "
    "بعبارة «من المجموعة:» وميّز بوضوح الجزء الذي هو من معرفتك العامة بعبارة «من معرفة AI:». ردود الطلاب غير مؤكدة "
    "الدقة فاذكر ذلك. لا تنسب أي معلومة للمجموعة إن لم تكن موجودة فعلًا في المقتطفات."
)

# ===== أنماط العمليات الدراسية =====
AI_MODE_META = {
    "summarize": {
        "label": "📚 تلخيص محاضرة",
        "prompt": (
            "أنت مساعد دراسي. لخّص المحتوى المرسل (محاضرة/ملف) بنقاط واضحة ومرتبة تغطي أهم "
            "الأفكار، بالعربية الفصحى المبسطة. لا تضف معلومات غير موجودة بالمصدر."
        ),
        "ask": "أرسل المحاضرة (نص أو ملف) وبلخصلك إياها.",
    },
    "explain": {
        "label": "📖 شرح محاضرة",
        "prompt": (
            "أنت مساعد دراسي. اشرح المحتوى المرسل بطريقة مبسطة ومنظمة، بأمثلة عند الحاجة، "
            "بالعربية الفصحى المبسطة."
        ),
        "ask": "أرسل المحاضرة (نص أو ملف) وبشرحلك إياها.",
    },
    "solve": {
        "label": "❓ مساعدة في حل سؤال",
        "prompt": (
            "أنت مساعد دراسي. ساعد الطالب يفهم ويحل السؤال المرسل خطوة بخطوة مع شرح كل خطوة، "
            "بالعربية الفصحى المبسطة."
        ),
        "ask": "أرسل السؤال (نص أو صورة) وبساعدك تحله خطوة بخطوة.",
    },
    "concept": {
        "label": "💡 مفهوم دراسي",
        "prompt": (
            "أنت مساعد دراسي. اشرح المفهوم الدراسي المرسل بشكل مبسط ومنظم مع أمثلة توضيحية، "
            "بالعربية الفصحى المبسطة."
        ),
        "ask": "اكتب اسم المفهوم أو أرسل نص/ملف فيه، وبشرحلك إياه.",
    },
    "translate": {
        "label": "🌐 ترجمة",
        "prompt": (
            "أنت مترجم دقيق. ترجم النص أو الملف المرسل بأمانة دون حذف أو إضافة معلومات. لو النص "
            "عربي ترجمه للإنجليزية، ولو إنجليزي ترجمه للعربية، إلا إذا حدد الطالب لغة أخرى صراحة."
        ),
        "ask": "أرسل النص أو الملف يلي بدك تترجمه.",
    },
    "exam_tf": {
        "label": "✅ أسئلة صح وخطأ",
        "prompt": (
            "أنت مساعد دراسي. اقرأ المحتوى المرسل وولّد منه 8 أسئلة صح/خطأ متنوعة تغطي أهم "
            "النقاط، واكتب الإجابة الصحيحة (صح/خطأ) بعد كل سؤال."
        ),
        "ask": "أرسل المادة (نص أو ملف) وبسوّيلك منها أسئلة صح وخطأ.",
    },
    "exam_mcq": {
        "label": "🔤 أسئلة اختيارات",
        "prompt": (
            "أنت مساعد دراسي. اقرأ المحتوى المرسل وولّد منه 8 أسئلة اختيار من متعدد (4 خيارات "
            "لكل سؤال)، وحدد الإجابة الصحيحة بعد كل سؤال."
        ),
        "ask": "أرسل المادة (نص أو ملف) وبسوّيلك منها أسئلة اختيارات.",
    },
    "exam_qa": {
        "label": "✍️ أسئلة وأجوبة",
        "prompt": (
            "أنت مساعد دراسي. اقرأ المحتوى المرسل وولّد منه 8 أسئلة مقالية (سؤال وجواب) تغطي "
            "أهم النقاط، مع إجابة نموذجية مختصرة لكل سؤال."
        ),
        "ask": "أرسل المادة (نص أو ملف) وبسوّيلك منها أسئلة وأجوبة.",
    },
}

AI_MODE_META["web"] = {
    "label": "🔎 بحث ويب",
    "prompt": AI_SYSTEM_PROMPT,
    "ask": "اكتب سؤالك وبدور عليه بالإنترنت وبجيبلك الجواب مع المصادر.",
}
AI_MODE_META["scholar"] = {
    "label": "🎓 بحث أكاديمي",
    "prompt": AI_SYSTEM_PROMPT,
    "ask": "اكتب موضوع البحث (يفضّل بالإنجليزية للأبحاث العلمية) وبجيبلك أوراق ومراجع أكاديمية.",
}

# ===== المساعد الدراسي العام =====
ASSISTANT_SYSTEM_PROMPT = (
    "أنت مساعد دراسي ذكي لطلاب جامعيين. مجالك: الدراسة والجامعة والتعلم (شرح، تلخيص، حل أسئلة ومسائل وأكواد بشكل تعليمي "
    "مع شرح الخطوات، ترجمة، مراجعة، تنظيم مذاكرة). افهم طلب الطالب وجاوب مباشرة بنفس لغته، بشكل منظم ومختصر إلا إذا احتاج تفصيل، "
    "بدون مقدمات أو خاتمة. إن كان الطلب بعيدًا عن الدراسة اعتذر بلطف. إذا لم تكن متأكدًا من معلومة محدّثة (رسوم، مواعيد) فقل ذلك صراحة."
)

ASSISTANT_FILE_PROMPT = (
    "أنت مساعد دراسي. حدد بنفسك المطلوب من المحتوى المرسل: إن كان سؤالًا أو مسألة فساعد الطالب بحلها خطوة بخطوة مع الشرح، "
    "وإن كان محاضرة أو نصًا دراسيًا فلخّصه بنقاط واضحة واشرح الأجزاء الصعبة، وإن طلب الطالب ترجمة فترجم. "
    "إن حدد الطالب طلبه بالتعليق فالتزم به. أجب بالعربية الفصحى المبسطة."
)

ASSISTANT_INTRO = (
    "🧑‍🏫 أنا مساعدك الدراسي. اكتب أي شي بخص دراستك: سؤال، شرح، تلخيص، حل مسألة، ترجمة، أو معلومة عن الجامعة "
    "(مثل رسوم أو تسجيل)، وأنا بفهم شو بدك وبرد عليك. وبتقدر تبعت نص أو ملف أو صورة."
)
NEED_CONTENT_REPLY = "تمام 👍 ابعتلي المحاضرة (نص، أو ملف PDF/Word/PowerPoint، أو صورة) وبشتغل عليها، أو اكتب اسم الموضوع وبشرحه لك."
OFF_TOPIC_REPLY = "هاد خارج نطاق الدراسة 🙂 أنا مساعد دراسي: اسألني عن مادة، أو بدك شرح، تلخيص، حل سؤال، أو معلومة عن الجامعة."

AI_MODE_META["assistant"] = {"label": "🧑‍🏫 مساعد دراسي", "prompt": ASSISTANT_SYSTEM_PROMPT, "ask": ASSISTANT_INTRO}

# ===== اختيار برومبت النمط =====
_BREVITY = " جاوب بإيجاز: قصير للسؤال البسيط، ومنظّم ومختصر للشرح، بدون مقدمات أو تكرار للسؤال أو خاتمة."

def mode_prompt(mode):
    p = AI_MODE_META.get(mode, {}).get("prompt", ASSISTANT_SYSTEM_PROMPT)
    return p if "بدون مقدمات" in p else p + _BREVITY


# =====================================================================
# ===== كتاب الطالب: استخراج -> تقطيع -> فهرسة -> سؤال/ملخص/شرح =====
# =====================================================================
_LOG = logging.getLogger("gpa5")

BOOK_MAX_PAGES = 600
BOOK_MAX_CHARS = 1_500_000
BOOKS_PER_USER = 3  # بنحتفظ بآخر 3 كتب لكل طالب والأقدم بينحذف تلقائيًا

BOOK_SUMMARY_PART_PROMPT = (
    "لخّص هذا الجزء من الكتاب بنقاط منظمة: المواضيع، المفاهيم والتعريفات، العلاقات، الأمثلة. "
    "لا تضف شيئًا غير موجود بالنص."
)
BOOK_SUMMARY_FINAL_PROMPT = (
    "هذه ملخصات أجزاء من كتاب واحد. ادمجها بملخص واحد منظم: المواضيع الرئيسية، المفاهيم والتعريفات، "
    "العلاقات بين المفاهيم، الأمثلة، ونقاط مهمة للامتحان. احذف التكرار ولا تضف شيئًا من خارج النص."
)
BOOK_NOT_FOUND = "ما لقيت جواب لهذا بالكتاب. جرب تعيد صياغة السؤال أو تذكر المصطلح بكلمات الكتاب نفسها."

BOOK_EXPLAIN_PROMPT = (
    "أنت مساعد دراسي. اشرح للطالب المقطع التالي من كتابه بطريقة مبسطة ومنظمة وبأمثلة عند الحاجة، "
    "واستند للنص أولًا. لا تنسب للكتاب شيئًا غير موجود فيه."
)
BOOK_OVERVIEW_PROMPT = (
    "هذه ملخصات أجزاء من كتاب واحد. اشرح للطالب شو موجود بالكتاب: الفصول أو المواضيع الرئيسية بالترتيب، "
    "وفكرة كل موضوع بجملتين. لا تضف شيئًا من خارج النص."
)


def llm_retry(fn, text, prompt, tries=3):
    """يعيد المحاولة لو فشل الاستدعاء (ضغط/حصة/رد فاضي) بدل ما تفشل العملية من أول تعثر."""
    last = None
    for i in range(tries):
        try:
            out = fn(text, prompt)
            if out and str(out).strip():
                return out
            last = RuntimeError("empty answer")
        except Exception as exc:
            last = exc
            _LOG.warning("llm attempt %s/%s failed: %s", i + 1, tries, exc)
        if i < tries - 1:
            time.sleep(2 * (i + 1))
    raise last


class BookCancelled(Exception):
    pass


class BookError(Exception):
    """رسالتها جاهزة تنعرض للطالب كما هي."""


class Progress:
    """حالة معالجة كتاب (بتتشارك بين خيط المعالجة ورسالة التقدم). stage: PREPARE -> EXTRACT -> INDEX -> READY"""

    def __init__(self):
        self.stage = "PREPARE"
        self.done = 0
        self.total = 0
        self.finished = False
        self.t0 = time.time()
        self.cancel = threading.Event()

    def check(self):
        if self.cancel.is_set():
            raise BookCancelled()


# ---------- تقطيع ----------
_SENT_SPLIT = re.compile(r"(?<=[.!?؟؛])\s+|\n")


def _clean(text):
    text = (text or "").replace("\r", "").replace("\x00", "")
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_long(par, max_chars):
    out, cur = [], ""
    for s in _SENT_SPLIT.split(par):
        s = s.strip()
        if not s:
            continue
        while len(s) > max_chars:
            cut = s.rfind(" ", 0, max_chars)
            cut = cut if cut > max_chars // 2 else max_chars
            if cur:
                out.append(cur)
                cur = ""
            out.append(s[:cut].strip())
            s = s[cut:].strip()
        if cur and len(cur) + 1 + len(s) > max_chars:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out


def chunk_text(text, max_chars=1200, overlap=150):
    """قطع بحجم تقريبي max_chars على حدود الفقرات مع تداخل بسيط."""
    text = _clean(text)
    if not text:
        return []
    pieces = []
    for par in re.split(r"\n\s*\n", text):
        par = par.strip()
        if par:
            pieces.extend(_split_long(par, max_chars) if len(par) > max_chars else [par])
    chunks, cur = [], ""
    for p in pieces:
        if cur and len(cur) + 2 + len(p) > max_chars:
            chunks.append(cur)
            tail = cur[-overlap:] if overlap > 0 else ""
            sp = tail.find(" ")
            tail = tail[sp + 1:] if 0 <= sp < len(tail) - 1 else tail
            cur = f"{tail}\n\n{p}".strip() if tail else p
        else:
            cur = f"{cur}\n\n{p}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def chunk_plain(text, max_chars=1200):
    """نص بلا صفحات (Word/PowerPoint/TXT): نفس شكل chunk_pages مع رقم صفحة 0 (= بلا صفحة)."""
    return [(c, 0, 0) for c in chunk_text(text, max_chars)]


def chunk_pages(pages, max_chars=1200, overlap=150):
    """يرجّع [(نص, صفحة_بداية, صفحة_نهاية)]: بنجمع الصفحات القصيرة المتجاورة ونقسّم الطويلة، وبنحفظ أرقام الصفحات للمصادر."""
    out, buf, start, end = [], "", None, None
    for n, t in enumerate(pages, 1):
        t = _clean(t)
        if not t:
            continue
        if buf and len(buf) + 2 + len(t) > max_chars:
            out.append((buf, start, end))
            buf, start = "", None
        if len(t) > max_chars:
            if buf:
                out.append((buf, start, end))
                buf, start = "", None
            out.extend((c, n, n) for c in chunk_text(t, max_chars, overlap))
            continue
        buf = f"{buf}\n\n{t}".strip()
        start = start or n
        end = n
    if buf:
        out.append((buf, start, end))
    return out


# ---------- استخراج PDF ----------
def _open_pdf(data):
    """يرجّع (عدد الصفحات، دالة تجيب نص صفحة). بنفضّل PyMuPDF لأنه أسرع بعشرات المرات من pypdf على السيرفرات الضعيفة."""
    mu = None
    try:
        try:
            import pymupdf as mu
        except ImportError:
            import fitz as mu
        if not hasattr(mu, "open"):  # حزمة fitz قديمة/غلط: منتجاهلها
            mu = None
    except ImportError:
        mu = None
    if mu is not None:
        try:
            doc = mu.open(stream=data, filetype="pdf")
            if doc.needs_pass and not doc.authenticate(""):
                raise BookError("ملف الـPDF محمي بكلمة سر.")
            return doc.page_count, (lambda i: doc.load_page(i).get_text("text") or "")
        except BookError:
            raise
        except Exception as exc:  # بنجرب pypdf قبل ما نستسلم
            _LOG.warning("pymupdf failed, falling back to pypdf: %s", exc)
    try:
        from pypdf import PdfReader
    except ImportError:
        raise BookError("ما في مكتبة لقراءة الـPDF على السيرفر. أضف pymupdf (الأسرع) أو pypdf لـrequirements وأعد التشغيل.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise BookError("ملف الـPDF محمي بكلمة سر.")
        return len(reader.pages), (lambda i: reader.pages[i].extract_text() or "")
    except BookError:
        raise
    except Exception:
        raise BookError("تعذرت قراءة ملف الـPDF، جرب ملف ثاني.")


def extract_pdf_pages(data, prog):
    """يرجّع قائمة نصوص الصفحات ويحدّث prog (stage=EXTRACT, done/total). يرمي BookError برسالة جاهزة."""
    n, get_text = _open_pdf(data)
    if n > BOOK_MAX_PAGES:
        raise BookError(f"الكتاب {n} صفحة، والحد الأقصى {BOOK_MAX_PAGES} صفحة.")
    prog.stage, prog.total, prog.done = "EXTRACT", n, 0
    pages, chars = [], 0
    for i in range(n):
        prog.check()
        try:
            t = get_text(i)
        except Exception:
            t = ""
        pages.append(t)
        chars += len(t)
        prog.done = i + 1
        if chars > BOOK_MAX_CHARS:
            raise BookError("نص الكتاب كبير زيادة عن الحد المسموح.")
    return pages


# ---------- التخزين والبحث ----------
_TASHKEEL = re.compile(r"[\u064b-\u0652\u0640\u0670]")
_WORD = re.compile(r"\w+", re.UNICODE)
_STOP = {"في", "من", "على", "الى", "إلى", "عن", "ما", "ماذا", "هو", "هي", "هل", "كيف", "شو", "ايش", "هاد", "هاي",
         "اشرح", "اشرحلي", "وضح", "عرف", "the", "a", "an", "of", "to", "is", "are", "what", "how", "and", "or"}


def normalize(text):
    t = _TASHKEEL.sub("", (text or "").lower())
    t = re.sub("[إأآ]", "ا", t)
    t = t.replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"\bال(?=\w{3,})", "", t)  # «الحلقات» و«حلقات» بيتطابقوا


_STOP = {normalize(w) for w in _STOP}  # الكلمات المهملة بنفس صيغة التوحيد


def query_terms(query, limit=8):
    seen, out = set(), []
    for w in _WORD.findall(normalize(query)):
        if len(w) < 2 or w in _STOP or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out[:limit]


class BookStore:
    """كتب الطالب مفهرسة بـFTS5 داخل ملف SQLite مستقل. كل استعلام مقيّد بـowner فما حدا بيشوف كتب غيره."""

    def __init__(self, db_path):
        self.db_path = db_path
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS gpa5_books (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                      "owner INTEGER NOT NULL, title TEXT NOT NULL, state TEXT NOT NULL, "
                      "pages INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS gpa5_chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                      "book_id INTEGER NOT NULL, owner INTEGER NOT NULL, idx INTEGER NOT NULL, "
                      "p1 INTEGER NOT NULL, p2 INTEGER NOT NULL, text TEXT NOT NULL)")
            c.execute("CREATE INDEX IF NOT EXISTS gpa5_chunks_book ON gpa5_chunks(book_id, idx)")
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS gpa5_fts USING fts5(norm)")

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=30)
        c.row_factory = sqlite3.Row
        return c

    def create_book(self, owner, title, pages=0):
        with self._conn() as c:
            return c.execute("INSERT INTO gpa5_books(owner,title,state,pages,created) VALUES(?,?,?,?,?)",
                             (int(owner), title[:200], "INDEXING", pages, int(time.time()))).lastrowid

    def set_state(self, book_id, state):
        with self._conn() as c:
            c.execute("UPDATE gpa5_books SET state=? WHERE id=?", (state, book_id))

    def current_book(self, owner):
        with self._conn() as c:
            r = c.execute("SELECT * FROM gpa5_books WHERE owner=? AND state='READY' ORDER BY id DESC LIMIT 1",
                          (int(owner),)).fetchone()
            return dict(r) if r else None

    def add_chunks(self, owner, book_id, chunks, prog=None):
        c = self._conn()
        try:
            c.execute("PRAGMA synchronous=OFF")
            c.execute("BEGIN")
            for i, (text, p1, p2) in enumerate(chunks):
                if prog is not None:
                    prog.check()
                    prog.done = i + 1
                cur = c.execute("INSERT INTO gpa5_chunks(book_id,owner,idx,p1,p2,text) VALUES(?,?,?,?,?,?)",
                                (book_id, int(owner), i, p1 or 0, p2 or 0, text))
                c.execute("INSERT INTO gpa5_fts(rowid,norm) VALUES(?,?)", (cur.lastrowid, normalize(text)))
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def pages_text(self, owner, book_id, p_from, p_to, max_chars=12000):
        """نص المقاطع اللي بتغطي الصفحات من p_from لـp_to (مرتبة)."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT text FROM gpa5_chunks WHERE book_id=? AND owner=? AND p1>0 AND p1<=? AND p2>=? ORDER BY idx",
                (book_id, int(owner), p_to, p_from)).fetchall()
        return "\n\n".join(r[0] for r in rows)[:max_chars]

    def chunks(self, owner, book_id):
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT idx,p1,p2,text FROM gpa5_chunks WHERE book_id=? AND owner=? ORDER BY idx",
                (book_id, int(owner)))]

    def search(self, owner, book_id, query, limit=6):
        terms = query_terms(query)
        if not terms:
            return []
        match = " OR ".join(f'"{t}"' for t in terms)
        with self._conn() as c:
            rows = [dict(r) for r in c.execute(
                "SELECT k.idx, k.p1, k.p2, k.text FROM gpa5_fts JOIN gpa5_chunks k ON k.id = gpa5_fts.rowid "
                "WHERE gpa5_fts MATCH ? AND k.owner=? AND k.book_id=? ORDER BY bm25(gpa5_fts) LIMIT ?",
                (match, int(owner), book_id, limit * 2))]
        need = min(2, len(terms))  # مقتطف فيه كلمة وحدة مشتركة بس غالبًا مش ذو صلة
        return [r for r in rows if sum(1 for t in terms if t in normalize(r["text"])) >= need][:limit]

    def delete_book(self, owner, book_id):
        with self._conn() as c:
            c.execute("DELETE FROM gpa5_fts WHERE rowid IN (SELECT id FROM gpa5_chunks WHERE book_id=? AND owner=?)",
                      (book_id, int(owner)))
            c.execute("DELETE FROM gpa5_chunks WHERE book_id=? AND owner=?", (book_id, int(owner)))
            c.execute("DELETE FROM gpa5_books WHERE id=? AND owner=?", (book_id, int(owner)))

    def trim_old(self, owner, keep=BOOKS_PER_USER):
        with self._conn() as c:
            ids = [r[0] for r in c.execute("SELECT id FROM gpa5_books WHERE owner=? ORDER BY id DESC",
                                           (int(owner),))][keep:]
        for bid in ids:
            self.delete_book(owner, bid)


def index_book(store, owner, title, chunks, pages, prog):
    """يفهرس الكتاب. لو انلغى أو فشل في النص بينحذف اللي انكتب منه، وما بيظهر كتاب ناقص."""
    prog.stage, prog.done, prog.total = "INDEX", 0, len(chunks)
    bid = store.create_book(owner, title, pages)
    try:
        store.add_chunks(owner, bid, chunks, prog)
        store.set_state(bid, "READY")
    except BaseException:
        store.delete_book(owner, bid)
        raise
    store.trim_old(owner)
    prog.stage = "READY"
    return bid


# ---------- العمليات على الكتاب (llm: دالة (user_text, system_prompt) -> str) ----------
def _pages_label(p1, p2):
    if not p1:
        return ""
    return f"ص {p1}" if p1 == p2 else f"ص {p1}-{p2}"


def _context(store, owner, book_id, query, max_chars=4500):
    parts, refs, total = [], [], 0
    for h in store.search(owner, book_id, query, 6):
        if parts and total + len(h["text"]) > max_chars:
            break
        pg = _pages_label(h["p1"], h["p2"])
        parts.append(f"[{len(parts) + 1}]" + (f" ({pg})" if pg else "") + f" {h['text']}")
        if pg and pg not in refs:
            refs.append(pg)
        total += len(h["text"])
    return "\n\n".join(parts), refs








def _book_batches(store, owner, book_id, batch_chars, max_batches):
    chunks = [c["text"] for c in store.chunks(owner, book_id)]
    batches, cur = [], ""
    for t in chunks:
        if cur and len(cur) + len(t) > batch_chars:
            batches.append(cur)
            cur = t
        else:
            cur = f"{cur}\n\n{t}".strip()
    if cur:
        batches.append(cur)
    if len(batches) > max_batches:  # كتاب طويل: بنوزّع الأجزاء المختارة على كامل الكتاب
        step = len(batches) / max_batches
        batches = [batches[int(i * step)] for i in range(max_batches)]
    return batches


def summarize_book(llm, store, owner, book_id, batch_chars=16000, max_batches=5, final_prompt=None):
    """map-reduce: أجزاء كبيرة (قليلة الاستدعاءات)، بتشتغل بالتوازي، وفشل جزء ما بيوقف الباقي."""
    from concurrent.futures import ThreadPoolExecutor
    final_prompt = final_prompt or BOOK_SUMMARY_FINAL_PROMPT
    batches = _book_batches(store, owner, book_id, batch_chars, max_batches)
    if not batches:
        return {"text": BOOK_NOT_FOUND, "used_llm": False}
    if len(batches) == 1:
        return {"text": llm_retry(llm, batches[0], final_prompt), "used_llm": True}

    def part(b):
        try:
            return llm_retry(llm, b, BOOK_SUMMARY_PART_PROMPT)
        except Exception as exc:
            _LOG.warning("summary part failed: %s", exc)
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        partials = [p for p in pool.map(part, batches) if p]
    if not partials:
        raise RuntimeError("all summary parts failed")
    joined = "\n\n".join(f"الجزء {i + 1}:\n{p}" for i, p in enumerate(partials))
    return {"text": llm_retry(llm, joined, final_prompt), "used_llm": True}


# =====================================================================
# ===== أمر /study كاملًا: الواجهة والتدفق ومعالجة الملفات والكتاب =====
# =====================================================================
class _MainNS:
    """بوابة لأسماء main.py (مزودات الذكاء، الحصص، الموجّه...). main بيمرّر globals() عبر setup()، فما في استيراد دائري."""
    ns = {}

    def __getattr__(self, name):
        try:
            return type(self).ns[name]
        except KeyError:
            raise AttributeError(f"main.py ما فيه الاسم {name}")


M = _MainNS()
_BOOKS = None  # بيتجهز بـsetup()
_mode_prompt = mode_prompt


def _env_int(name, default):
    """رقم من البيئة؛ لو القيمة غلط بنرجع للافتراضي بدل ما يقع البوت وقت الإقلاع."""
    raw = os.environ.get(name, "")
    try:
        return int(raw) if raw.strip() else default
    except ValueError:
        _LOG.warning("قيمة غير صالحة للمتغير %s؛ استخدمنا الافتراضي %s", name, default)
        return default


DOC_MAX_MEMBER_BYTES = _env_int("DOC_MAX_MEMBER_BYTES", 20 * 1024 * 1024)   # أقصى حجم ملف داخل docx/pptx بعد فك الضغط

DOC_MAX_TOTAL_BYTES = _env_int("DOC_MAX_TOTAL_BYTES", 60 * 1024 * 1024)

DOC_MAX_MEMBERS = _env_int("DOC_MAX_MEMBERS", 3000)

DOC_MAX_TEXT_CHARS = _env_int("DOC_MAX_TEXT_CHARS", 200_000)

def ask_gemini_file(file_bytes, mime_type, system_prompt, caption=""):
    parts = [{"inline_data": {"mime_type": mime_type, "data": base64.b64encode(file_bytes).decode()}}]
    if caption.strip():
        parts.append({"text": caption.strip()})
    return M._scrub_identity(M._gemini_generate(M._persona(system_prompt), parts, timeout=90))  # الصور/PDF: متعدد الوسائط فقط

def _file_prompt(hint, caption=""):
    """نوع العملية لملف/صورة: تعليق الطالب (لخص/ترجم...) أول، ثم النمط الحالي كتلميح، وإلا بيحدد النموذج بنفسه."""
    vm = M._verb_mode(caption) if caption else None
    mode = vm[0] if vm else hint
    if mode in M._CONTENT_HINTS:
        return _mode_prompt(mode)
    return ASSISTANT_FILE_PROMPT

AI_SUPPORTED_FILES_NOTE = "📚 يدعم البوت: PDF, DOCX, PPTX, TXT، وصور (JPG/PNG)."

MAX_AI_FILE_MB = 15
BOOK_MAX_FILE_MB = _env_int("GPA5_MAX_FILE_MB", 20)  # حد تحميل البوتات من تيليجرام = 20MB



def _zip_open_checked(data):
    """يفتح docx/pptx بعد فحص حدود الحجم قبل فك الضغط (حماية من zip bomb)."""
    z = zipfile.ZipFile(io.BytesIO(data))
    infos = z.infolist()
    if len(infos) > DOC_MAX_MEMBERS or sum(i.file_size for i in infos) > DOC_MAX_TOTAL_BYTES:
        z.close()
        raise M.UserFacingError("الملف كبير أو معقّد زيادة بعد فك الضغط. جرّب تصديره PDF وإعادة إرساله.")
    return z

def _zip_read_limited(z, name):
    info = z.getinfo(name)
    if info.file_size > DOC_MAX_MEMBER_BYTES:
        raise M.UserFacingError("جزء من الملف كبير زيادة. جرّب تصديره PDF وإعادة إرساله.")
    with z.open(info) as f:
        raw = f.read(DOC_MAX_MEMBER_BYTES + 1)  # حد فعلي حتى لو الترويسة مزوّرة
    if len(raw) > DOC_MAX_MEMBER_BYTES:
        raise M.UserFacingError("جزء من الملف كبير زيادة. جرّب تصديره PDF وإعادة إرساله.")
    if b"<!DOCTYPE" in raw[:4096].upper() or b"<!ENTITY" in raw[:65536].upper():
        raise M.UserFacingError("تعذرت قراءة هذا الملف، جرب تصديره PDF وإعادة إرساله.")
    return raw

def _extract_docx_text(data):
    try:
        with _zip_open_checked(data) as z:
            xml_bytes = _zip_read_limited(z, "word/document.xml")
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        root = ET.fromstring(xml_bytes)
        paragraphs = []
        for p in root.iter(f"{ns}p"):
            texts = [t.text for t in p.iter(f"{ns}t") if t.text]
            if texts:
                paragraphs.append("".join(texts))
        return "\n".join(paragraphs)[:DOC_MAX_TEXT_CHARS]
    except M.UserFacingError:
        raise
    except Exception as exc:
        M._NLOG.warning(f"docx extraction error: {exc}")
        raise M.UserFacingError("تعذرت قراءة هذا الملف، جرب تصديره PDF وإعادة إرساله.")

def _extract_pptx_text(data):
    try:
        lines = []
        with _zip_open_checked(data) as z:
            slide_files = sorted(
                (n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                key=lambda n: int(re.search(r"\d+", n).group())
            )
            ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
            for name in slide_files:
                root = ET.fromstring(_zip_read_limited(z, name))
                texts = [t.text for t in root.iter(f"{ns}t") if t.text]
                if texts:
                    lines.append(" ".join(texts))
                if sum(len(x) for x in lines) > DOC_MAX_TEXT_CHARS:
                    break
        return "\n".join(lines)[:DOC_MAX_TEXT_CHARS]
    except M.UserFacingError:
        raise
    except Exception as exc:
        M._NLOG.warning(f"pptx extraction error: {exc}")
        raise M.UserFacingError("تعذرت قراءة هذا الملف، جرب تصديره PDF وإعادة إرساله.")

async def _download_telegram_file(context, file_id):
    tg_file = await context.bot.get_file(file_id)
    buf = io.BytesIO()
    await tg_file.download_to_memory(out=buf)
    return buf.getvalue()

_BOOK_JOBS = {}                  # uid -> Progress لمعالجة كتاب جارية (واحدة لكل طالب)

_BOOK_SEM = asyncio.Semaphore(2)  # معالجتين بالتوازي كحد أقصى حتى ما يتعب السيرفر المجاني

_BOOK_STAGES = (("PREPARE", "تحضير"), ("EXTRACT", "استخراج"), ("INDEX", "فهرسة"), ("READY", "جاهز"))

def _book_for(uid):
    try:
        return _BOOKS.current_book(uid) if _BOOKS else None
    except Exception:
        M._log_exc("قراءة كتاب الطالب")
        return None

def _job_pct(job):
    if job.stage == "PREPARE":
        return 2
    frac = (job.done / job.total) if job.total else 0
    if job.stage == "EXTRACT":
        return int(5 + 60 * frac)
    if job.stage == "INDEX":
        return int(65 + 34 * frac)
    return 100

def _fmt_secs(sec):
    sec = int(sec)
    return f"{sec}ث" if sec < 60 else f"{sec // 60}د {sec % 60:02d}ث"


def _job_text(title, job):
    idx = [k for k, _l in _BOOK_STAGES].index(job.stage)
    marks = " ".join(("●" if i <= idx else "○") + label for i, (_k, label) in enumerate(_BOOK_STAGES))
    pct = _job_pct(job)
    bar = "▓" * (pct // 10) + "░" * (10 - pct // 10)
    detail = ""
    if job.stage == "EXTRACT" and job.total:
        detail = f"\nتم تجهيز {job.done} من {job.total} صفحة"
        if job.done >= 3:
            left = (time.time() - job.t0) / job.done * (job.total - job.done)
            if left >= 5:
                detail += f"\n⏱ باقي حوالي {_fmt_secs(left)}"
    elif job.stage == "INDEX" and job.total:
        detail = f"\nفهرسة {job.done} من {job.total} مقطع"
    return f"⏳ جاري معالجة الكتاب\n📘 {title}\n\n{marks}\n{bar} {pct}%{detail}"

def _stop_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⛔ إيقاف المعالجة", callback_data="ai:book_stop")]])

def _study_text(uid):
    job = _BOOK_JOBS.get(uid)
    book = None if job else _book_for(uid)
    if _BOOKS is None:
        head = "📚 الكتاب: الميزة مش متاحة حاليًا."
    elif job:
        head = f"📚 الكتاب: ⏳ قيد المعالجة ({_job_pct(job)}%)"
    elif book:
        head = f"📚 الكتاب: «{book['title']}» ✅ جاهز\nأسئلتك بجاوبها منه أولًا."
    else:
        head = "📚 الكتاب: لسا ما أضفت كتاب.\nابعت ملف PDF أو Word أو PowerPoint وبشتغل عليه."
    return (
        "🧠 مساحة الذكاء\n\n"
        f"{head}\n\n"
        "اختر من الأزرار، أو اكتب أي شي وبفهمه لحاله:\n"
        "• سؤال أو مفهوم أو رقم صفحة\n"
        "• حل مسألة أو ترجمة\n"
        "• بحث بالإنترنت أو أبحاث أكاديمية\n\n"
        "⚠️ قد يخطئ الذكاء، تحقق من المعلومات المهمة."
    )

def _study_keyboard(uid):
    rows = [
        [InlineKeyboardButton("📖 شرح", callback_data="ai:explain"),
         InlineKeyboardButton("📚 ملخص", callback_data="ai:summarize")],
        [InlineKeyboardButton("📝 اختباري", callback_data="ai:exam_mcq"),
         InlineKeyboardButton("✍️ مقالي", callback_data="ai:exam_qa")],
    ]
    if _BOOKS is not None:
        if uid in _BOOK_JOBS:
            rows.append([InlineKeyboardButton("⛔ إيقاف المعالجة", callback_data="ai:book_stop")])
        elif _book_for(uid):
            rows.append([InlineKeyboardButton("📎 كتاب جديد", callback_data="ai:book_new"),
                         InlineKeyboardButton("🗑 حذف الكتاب", callback_data="ai:book_del")])
        else:
            rows.append([InlineKeyboardButton("📎 إضافة كتاب", callback_data="ai:book_new")])
    rows.append(M._home_row())
    return InlineKeyboardMarkup(rows)

def _book_build(title, name, data, uid, job):
    """يشتغل بخيط منفصل: استخراج -> تقطيع -> فهرسة. يرمي BookError/BookCancelled."""
    job.check()
    if name.endswith(".pdf"):
        pages = extract_pdf_pages(data, job)
        chunks, n_pages = chunk_pages(pages), len(pages)
    else:
        job.stage = "EXTRACT"
        if name.endswith(".docx"):
            text = _extract_docx_text(data)
        elif name.endswith(".pptx"):
            text = _extract_pptx_text(data)
        else:
            text = data.decode("utf-8", errors="ignore")
        chunks, n_pages = chunk_plain(text), 0
    t_extract = time.time() - job.t0
    job.check()
    if not chunks:
        raise BookError("ما لقيت نص قابل للقراءة بالملف (غالبًا ممسوح ضوئيًا كصور).")
    index_book(_BOOKS, uid, title, chunks, n_pages, job)
    _LOG.info("gpa5 book ready: pages=%s chunks=%s extract=%.1fs total=%.1fs", n_pages, len(chunks), t_extract, time.time() - job.t0)

async def _book_progress_loop(msg, title, job):
    last = None
    while not job.finished:
        await asyncio.sleep(2.5)
        text = _job_text(title, job)
        if text == last:
            continue
        last = text
        try:
            await msg.edit_text(text, reply_markup=_stop_keyboard())
        except RetryAfter as exc:
            await asyncio.sleep(exc.retry_after + 1)
        except Exception:
            pass

async def _book_ingest(update, context):
    uid, chat, doc = update.effective_user.id, update.effective_chat, update.message.document
    if _BOOKS is None:
        await update.message.reply_text("⚠️ ميزة الكتاب مش متاحة حاليًا.")
        return M.AI_TEXT
    if uid in _BOOK_JOBS:
        await update.message.reply_text("⏳ في كتاب قيد المعالجة، استنى يخلص أو اضغط إيقاف.")
        return M.AI_TEXT
    name = (doc.file_name or "").lower()
    if not name.endswith((".pdf", ".docx", ".pptx", ".txt")):
        await update.message.reply_text("⚠️ الكتاب لازم يكون PDF أو Word أو PowerPoint أو TXT.")
        return M.AI_TEXT
    if doc.file_size and doc.file_size > BOOK_MAX_FILE_MB * 1024 * 1024:
        await update.message.reply_text(f"⚠️ الكتاب أكبر من {BOOK_MAX_FILE_MB}MB (حد تيليجرام للبوتات). جرب تضغط الملف وابعته من جديد.")
        return M.AI_TEXT
    title = os.path.splitext(doc.file_name or "كتاب")[0][:80] or "كتاب"
    job = Progress()
    _BOOK_JOBS[uid] = job
    msg = await update.message.reply_text(_job_text(title, job), reply_markup=_stop_keyboard())
    ticker = asyncio.create_task(_book_progress_loop(msg, title, job))
    result = None
    try:
        async with _BOOK_SEM:
            data = await _download_telegram_file(context, doc.file_id)
            await asyncio.to_thread(_book_build, title, name, data, uid, job)
        done_book = _book_for(uid) or {}
        pages_txt = f"{done_book['pages']} صفحة، " if done_book.get("pages") else ""
        result = f"✅ جهز الكتاب: «{title}» ({pages_txt}خلال {_fmt_secs(time.time() - job.t0)})"
    except BookCancelled:
        result = "⛔ تم إيقاف المعالجة."
    except (BookError, M.UserFacingError) as exc:
        result = f"⚠️ {exc}"
    except Exception as exc:
        M._log_failure("معالجة كتاب", exc, uid)
        result = "⚠️ تعذرت معالجة الكتاب، جرب ملف ثاني."
    finally:
        job.finished = True
        _BOOK_JOBS.pop(uid, None)
        ticker.cancel()
        try:
            await ticker
        except asyncio.CancelledError:
            pass
    context.user_data.pop("ai_mode", None)
    try:
        await msg.edit_text(result)
    except Exception:
        await chat.send_message(result)
    await chat.send_message(_study_text(uid), reply_markup=_study_keyboard(uid))
    return M.AI_TEXT


async def _book_callback(update, context, data):
    query = update.callback_query
    uid = query.from_user.id
    action = data.split(":", 1)[1]
    M._set_flow(update, "ai")

    async def card(prefix=""):
        await M._safe_edit(query, prefix + _study_text(uid), _study_keyboard(uid))
        return M.AI_TEXT

    if _BOOKS is None:
        return await card("⚠️ ميزة الكتاب مش متاحة حاليًا.\n\n")
    if action == "book_stop":
        job = _BOOK_JOBS.get(uid)
        if job:
            job.cancel.set()
        return M.AI_TEXT
    if action == "book_new":
        if uid in _BOOK_JOBS:
            return await card("⏳ في كتاب قيد المعالجة، استنى يخلص أو اضغط إيقاف.\n\n")
        context.user_data["ai_mode"] = "book_add"
        await M._safe_edit(query, f"📎 ابعت ملف الكتاب (PDF أو Word أو PowerPoint، حتى {BOOK_MAX_FILE_MB}MB).\n"
                                  "بعد ما يجهز، الشرح والملخص والاختباري وأسئلتك كلها بتشتغل عليه.")
        return M.AI_TEXT
    if action == "book_del":
        book = _book_for(uid)
        if book:
            _BOOKS.delete_book(uid, book["id"])
        context.user_data.pop("ai_mode", None)
        return await card("🗑 انحذف الكتاب.\n\n")
    return await card()


_STUDY_ACTIONS = ("explain", "summarize", "exam_mcq", "exam_qa")


async def _action_callback(update, context, mode):
    """شرح / ملخص / اختباري / مقالي: بتشتغل على الكتاب إذا موجود، وإلا على اللي بيبعته الطالب (نص/ملف/صورة)."""
    query = update.callback_query
    uid, chat = query.from_user.id, update.effective_chat
    M._set_flow(update, "ai")
    context.user_data["ai_mode"] = mode
    meta = AI_MODE_META[mode]
    book = None if uid in _BOOK_JOBS else _book_for(uid)
    if not book:
        await M._safe_edit(query, f"{meta['ask']}\n\n{AI_SUPPORTED_FILES_NOTE}\nوبتقدر تكتب أي طلب ثاني بأي وقت، بفهمه لحاله.")
        return M.AI_TEXT
    if mode == "explain":
        await M._safe_edit(query, f"📖 اكتب شو بدك أشرحه من «{book['title']}»:\n• مفهوم أو سؤال\n• رقم الصفحة (مثلًا: صفحة 12 أو 12-15)\n• أو اكتب «شو موجود بالكتاب» لنظرة عامة")
        return M.AI_TEXT
    if not M._ai_quota_ok(uid):
        await chat.send_message(f"⏳ وصلت الحد اليومي لاستخدام المساعد الذكي ({M.AI_DAILY_LIMIT} طلب/يوم). جرب بكرة.")
        return M.AI_TEXT
    what = "بلخّص" if mode == "summarize" else "بجهّز أسئلة من"
    await M._safe_edit(query, f"⏳ عم {what} «{book['title']}»… ممكن ياخد دقيقة.")
    try:
        if mode == "summarize":
            res = await asyncio.to_thread(summarize_book, M.ask_gemini, _BOOKS, uid, book["id"])
        else:
            sample = await asyncio.to_thread(sample_book_text, _BOOKS, uid, book["id"])
            res = {"text": await asyncio.to_thread(M.ask_gemini, sample, _mode_prompt(mode)), "used_llm": True} if sample \
                else {"text": BOOK_NOT_FOUND, "used_llm": False}
        if res["used_llm"]:
            M._count_ai_answer(uid)
        await M._send_long(chat, res["text"])
    except Exception as exc:
        M._log_failure("عملية على الكتاب", exc, uid)
        await chat.send_message(M.friendly_error(exc))
    await chat.send_message(_study_text(uid), reply_markup=_study_keyboard(uid))
    return M.AI_TEXT

async def ai_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    if await M._maintenance_block(update):
        return ConversationHandler.END
    M._set_flow(update, "ai")
    context.user_data.pop("ai_mode", None)
    uid = update.effective_user.id
    text, kb = _study_text(uid), _study_keyboard(uid)
    if update.callback_query:
        await M._safe_edit(update.callback_query, text, kb)
    else:
        await update.effective_chat.send_message(text, reply_markup=kb)
    return M.AI_TEXT

async def ai_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id

    # الرئيسية، وكمان أزرار قوائم قديمة (أدوات/أسئلة امتحان) بتضل بالرسائل القديمة: كلها بترجع للشاشة الموحدة
    if data in ("ai:menu", "ai:tools", "ai:exam_menu"):
        M._set_flow(update, "ai")
        context.user_data.pop("ai_mode", None)
        await M._safe_edit(query, _study_text(uid), _study_keyboard(uid))
        return M.AI_TEXT
    if data.startswith("ai:book_"):
        return await _book_callback(update, context, data)

    mode = data.split(":", 1)[1]
    if mode in _STUDY_ACTIONS:
        return await _action_callback(update, context, mode)
    meta = AI_MODE_META.get(mode)  # أزرار قديمة (مساعد/ترجمة/حل...) لسا بتشتغل لو انضغطت من رسالة قديمة
    if not meta:
        await M._safe_edit(query, _study_text(uid), _study_keyboard(uid))
        return M.AI_TEXT
    context.user_data["ai_mode"] = mode
    M._set_flow(update, "ai")
    await M._safe_edit(query, f"{meta['ask']}\n\n{AI_SUPPORTED_FILES_NOTE}\nوبتقدر تكتب أي طلب ثاني بأي وقت، بفهمه لحاله.")
    return M.AI_TEXT

async def ai_assistant_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await M._maintenance_block(update):
        return ConversationHandler.END
    M._set_flow(update, "ai")
    context.user_data["ai_mode"] = "assistant"
    await update.effective_chat.send_message(f"{ASSISTANT_INTRO}\n\n{AI_SUPPORTED_FILES_NOTE}")
    return M.AI_TEXT

async def ai_exit_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    M._clear_flow(update)
    await M.home_callback(update, context)
    return ConversationHandler.END

def uid_not_busy(update):
    return update.effective_user.id not in _BOOK_JOBS


async def ai_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("أرسل نصًا أو ملفًا مدعومًا.")
        return M.AI_TEXT
    mode = context.user_data.get("ai_mode")
    if mode == "book_add":
        await update.message.reply_text("📎 ابعت ملف الكتاب (PDF أو Word أو PowerPoint). للرجوع اضغط /study")
        return M.AI_TEXT
    # كتاب جاهز: صفحة/نظرة عامة/شرح بالنمط «شرح» بنعالجها هون مباشرة، وأي شي ثاني بيكمل للموجّه
    if _BOOKS is not None and mode in (None, "explain") and uid_not_busy(update):
        book = _book_for(update.effective_user.id)
        if book and (mode == "explain" or parse_book_request(text)[0] != "concept"):
            uid = update.effective_user.id
            if not M._ai_quota_ok(uid):
                return await M._ai_quota_block(update)
            wait = await update.message.reply_text("⏳ عم قرأ الكتاب…")
            try:
                res = await asyncio.to_thread(explain_from_book, uid, text, book)
            except Exception as exc:
                M._log_failure("شرح من الكتاب", exc, uid)
                await M._delete_quiet(wait)
                await update.message.reply_text(M.friendly_error(exc))
                return M.AI_TEXT
            await M._delete_quiet(wait)
            if res:
                if res["used_llm"]:
                    M._count_ai_answer(uid)
                await M._send_long(update.effective_chat, res["text"])
                return M.AI_TEXT
    # النمط المختار مجرد تلميح: نفس الموجّه الموحّد، وأي طلب مختلف (مكتبة/Moodle...) بيروح لوجهته مباشرة
    keep = await M._route_message(update, context, text, context.user_data.get("ai_mode"))
    return M.AI_TEXT if keep else ConversationHandler.END

async def ai_receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("ai_mode") == "book_add":
        await update.message.reply_text("📎 ابعت الكتاب كملف (PDF أو Word أو PowerPoint) مش كصورة.")
        return M.AI_TEXT
    uid = update.effective_user.id
    if not M._ai_quota_ok(uid):
        return await M._ai_quota_block(update)
    caption = (update.message.caption or "").strip()
    system_prompt = _file_prompt(M._current_hint(update, context), caption)
    status_msg = await update.message.reply_text("⏳ بشوف الصورة…")
    try:
        data = await _download_telegram_file(context, update.message.photo[-1].file_id)
        answer = await asyncio.to_thread(ask_gemini_file, data, "image/jpeg", system_prompt, caption)
        M._count_ai_answer(uid)
        await M._delete_quiet(status_msg)
        await M._send_long(update.effective_chat, answer)
    except Exception as exc:
        M._log_failure("تحليل صورة", exc, uid)
        await M._delete_quiet(status_msg)
        await update.message.reply_text(M.friendly_error(exc))
    return M.AI_TEXT

async def ai_receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("ai_mode") == "book_add":
        return await _book_ingest(update, context)
    uid = update.effective_user.id
    if not M._ai_quota_ok(uid):
        return await M._ai_quota_block(update)
    doc = update.message.document
    if doc.file_size and doc.file_size > MAX_AI_FILE_MB * 1024 * 1024:
        await update.message.reply_text(f"⚠️ الملف أكبر من {MAX_AI_FILE_MB}MB، جرب ملف أصغر.")
        return M.AI_TEXT
    name = (doc.file_name or "").lower()
    if not name.endswith((".pdf", ".docx", ".pptx", ".txt", ".jpg", ".jpeg", ".png", ".webp")):
        await update.message.reply_text(f"⚠️ صيغة الملف هاي مش مدعومة حاليًا.\n{AI_SUPPORTED_FILES_NOTE}")
        return M.AI_TEXT
    caption = (update.message.caption or "").strip()
    system_prompt = _file_prompt(M._current_hint(update, context), caption)  # العملية واضحة من التعليق/النمط: بدون موجّه
    status_msg = await update.message.reply_text("⏳ بقرأ الملف…")
    try:
        data = await _download_telegram_file(context, doc.file_id)
        if name.endswith(".pdf"):
            answer = await asyncio.to_thread(ask_gemini_file, data, "application/pdf", system_prompt, caption)
        elif name.endswith((".jpg", ".jpeg", ".png", ".webp")):
            mime = "image/png" if name.endswith(".png") else ("image/webp" if name.endswith(".webp") else "image/jpeg")
            answer = await asyncio.to_thread(ask_gemini_file, data, mime, system_prompt, caption)
        else:
            if name.endswith(".docx"):
                extracted = _extract_docx_text(data)
            elif name.endswith(".pptx"):
                extracted = _extract_pptx_text(data)
            else:
                extracted = data.decode("utf-8", errors="ignore")
            answer = await asyncio.to_thread(M.ask_gemini, (caption + "\n\n" + extracted).strip(), system_prompt)
        M._count_ai_answer(uid)
        await M._delete_quiet(status_msg)
        await M._send_long(update.effective_chat, answer)
    except RuntimeError as exc:
        await M._delete_quiet(status_msg)
        await update.message.reply_text(M.friendly_error(exc))
    except Exception as exc:
        M._NLOG.warning(f"file extraction error: {exc}")
        await M._delete_quiet(status_msg)
        await update.message.reply_text("⚠️ تعذرت معالجة هذا الملف، جرب صيغة أخرى.")
    return M.AI_TEXT

async def ai_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    M._clear_flow(update)
    context.user_data.pop("ai_mode", None)
    await update.message.reply_text("تم الإلغاء.")
    return ConversationHandler.END


BOOK_GROUNDING_RULES = (
    "\n\nعندك مقتطفات من كتاب الطالب. استخدمها أولًا إذا ارتبطت بالسؤال، وابدأ الجزء المأخوذ منها بعبارة "
    "«من الكتاب:» (مع رقم الصفحة إن وُجد)، وميّز أي إضافة من عندك بعبارة «من معرفتي:». "
    "لا تنسب للكتاب شيئًا غير موجود فعلًا بالمقتطفات."
)


_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_PAGE_RE = re.compile(
    r"(?:صفح[ةه]|صفحات|ص|pages?|p)\s*\.?\s*(\d{1,4})(?:\s*(?:-|–|الى|إلى|لحد|to)\s*(\d{1,4}))?", re.I)
_OVERVIEW = ("موجود", "محتوي", "محتويات", "فهرس", "عن شو", "عن ماذا", "كل الكتاب", "الكتاب كامل", "الكتاب كله")


def parse_book_request(text):
    """('page', a, b) أو ('overview',) أو ('concept',)"""
    t = (text or "").translate(_DIGITS)
    m = _PAGE_RE.search(t)
    if m:
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        a, b = min(a, b), min(max(a, b), min(a, b) + 9)  # حد أقصى 10 صفحات بالطلب
        return ("page", a, b)
    n = normalize(t)
    if any(k in n for k in _OVERVIEW):
        return ("overview",)
    return ("concept",)


def explain_from_book(uid, text, book):
    """يرجّع {"text","used_llm"} أو None لو الطلب مش من الكتاب (بيكمل المسار العادي)."""
    kind = parse_book_request(text)
    if kind[0] == "page":
        body = _BOOKS.pages_text(uid, book["id"], kind[1], kind[2])
        if not body:
            return {"text": f"ما لقيت نص للصفحة {kind[1]} بالكتاب (الكتاب {book.get('pages') or '؟'} صفحة، "
                            "وممكن تكون الصفحة صورة بدون نص).", "used_llm": False}
        return {"text": llm_retry(M.ask_gemini, body, BOOK_EXPLAIN_PROMPT), "used_llm": True}
    if kind[0] == "overview":
        return summarize_book(M.ask_gemini, _BOOKS, uid, book["id"], final_prompt=BOOK_OVERVIEW_PROMPT)
    ctx, _refs = _context(_BOOKS, uid, book["id"], text)
    if not ctx:
        return None
    return {"text": llm_retry(M.ask_gemini, f"سؤال الطالب: {text}\n\nمقتطفات من الكتاب:\n{ctx}",
                              BOOK_EXPLAIN_PROMPT + BOOK_GROUNDING_RULES), "used_llm": True}


def book_grounding(uid, text):
    """مقتطفات من كتاب الطالب ذات صلة بسؤاله (أو نص فارغ). main._answer_ai بيستدعيها قبل بحث الأرشيف."""
    if _BOOKS is None:
        return ""
    try:
        book = _BOOKS.current_book(uid)
        if not book:
            return ""
        ctx, _refs = _context(_BOOKS, uid, book["id"], text)
        return ctx
    except Exception:
        M._log_exc("سياق الكتاب")
        return ""


def sample_book_text(store, owner, book_id, chars=6000):
    """عيّنة موزعة على الكتاب (مختلفة كل مرة) لتوليد أسئلة الاختباري/المقالي."""
    chunks = [c["text"] for c in store.chunks(owner, book_id)]
    if not chunks:
        return ""
    per = max(1, chars // 1200)
    step = max(1, len(chunks) // per)
    off = random.randrange(step) if step > 1 else 0
    return "\n\n".join(chunks[off::step][:per])[:chars]


def setup(ns):
    """بيستدعيها main.py مرة وحدة قبل تسجيل الأوامر: بتربط أسماء main وبتفتح قاعدة الكتب."""
    global _BOOKS
    _MainNS.ns = ns
    try:
        _BOOKS = BookStore(os.environ.get("GPA5_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpa5_books.db")))
    except Exception as exc:  # الميزة بتتعطل لحالها والبوت بيكمل شغله
        _LOG.warning("gpa5 books disabled: %s", exc)
        _BOOKS = None


def build_conversation():
    return ConversationHandler(
        entry_points=[
            CommandHandler(["study", "ask"], ai_start),  # /ask اسم قديم بيفتح نفس الشاشة
            CommandHandler("assistant", ai_assistant_cmd),
            CallbackQueryHandler(ai_start, pattern="^ask$"),
            CallbackQueryHandler(ai_menu_callback, pattern="^ai:"),  # أزرار قديمة بعد إعادة تشغيل البوت
        ],
        states={
            M.AI_MODE: [CallbackQueryHandler(ai_menu_callback, pattern="^ai:")],
            M.AI_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & M.AI_FLOW_FILTER, ai_receive),
                MessageHandler(filters.Document.ALL & M.AI_FLOW_FILTER, ai_receive_file),
                MessageHandler(filters.PHOTO & M.AI_FLOW_FILTER, ai_receive_photo),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", ai_cancel),
            CallbackQueryHandler(ai_exit_home, pattern="^home$"),
        ],
        per_chat=True,
        per_user=True,
        allow_reentry=True,
        conversation_timeout=900,  # المحادثة المنسية بتنتهي لحالها بعد 15 دقيقة
    )
