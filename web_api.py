import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

_LOG = logging.getLogger("nexis.web")
_SERVER = None
_THREAD = None
_BACKEND = None

TOKEN_TTL = int(os.environ.get("WEB_SESSION_TTL", 60 * 60 * 24 * 30))
TELEGRAM_AUTH_MAX_AGE = int(os.environ.get("TELEGRAM_AUTH_MAX_AGE", 86400))


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _secret():
    value = getattr(_BACKEND, "MASTER_KEY", "") or getattr(_BACKEND, "BOT_TOKEN", "")
    if not value:
        raise RuntimeError("Missing backend secret")
    return value.encode()


def _make_token(uid):
    payload = {
        "uid": int(uid),
        "exp": int(time.time()) + TOKEN_TTL,
    }
    raw = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_secret(), raw.encode(), hashlib.sha256).digest())
    return raw + "." + sig


def _read_token(header):
    if not header or not header.startswith("Bearer "):
        return None

    try:
        raw, sig = header[7:].split(".", 1)
        expected = _b64(
            hmac.new(_secret(), raw.encode(), hashlib.sha256).digest()
        )

        if not hmac.compare_digest(sig, expected):
            return None

        payload = json.loads(_unb64(raw))

        if int(payload["exp"]) < int(time.time()):
            return None

        return int(payload["uid"])
    except Exception:
        return None


def _telegram_valid(data):
    bot_token = getattr(_BACKEND, "BOT_TOKEN", "")

    if not bot_token:
        return False

    try:
        auth_date = int(data.get("auth_date", 0))

        if abs(int(time.time()) - auth_date) > TELEGRAM_AUTH_MAX_AGE:
            return False

        received = str(data.get("hash", ""))

        pairs = []
        for key in sorted(data):
            if key == "hash":
                continue

            value = data[key]

            if value is None:
                continue

            pairs.append(f"{key}={value}")

        check_string = "\n".join(pairs).encode()

        secret = hashlib.sha256(bot_token.encode()).digest()

        expected = hmac.new(
            secret,
            check_string,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(received, expected)

    except Exception:
        return False


def _json(data):
    return json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _user(uid):
    return _BACKEND.get_user(uid)


def _overview(uid, fresh=False):
    row = _user(uid)

    if not row:
        return {
            "linked": False,
            "courses": [],
            "assignments": [],
            "exams": [],
            "fetched_at": int(time.time()),
        }

    session = _BACKEND.get_moodle_session(uid, row, fresh=fresh)
    courses = _BACKEND.get_courses(session, "inprogress")

    out_courses = []
    assignments = []
    exams = []

    for course_name, course_url in courses:
        try:
            ce, ca, materials, _week, extra = (
                _BACKEND.get_activities_for_course(
                    session, course_url
                )
            )
        except Exception as exc:
            _LOG.warning(
                "web Moodle course failed: %s (%s)",
                course_name,
                type(exc).__name__,
            )
            out_courses.append({
                "name": course_name,
                "url": course_url,
                "materials": 0,
                "error": True,
            })
            continue

        out_courses.append({
            "name": course_name,
            "url": course_url,
            "materials": len(materials),
        })

        completion = extra.get("completion", {})

        for item in ca:
            name, opened, due, link = item
            assignments.append({
                "course": course_name,
                "name": name,
                "opened": opened,
                "due": due,
                "link": link,
                "done": completion.get(link),
            })

        for item in ce:
            name, opened, closed, *rest = item
            link = rest[-1] if rest else None
            exams.append({
                "course": course_name,
                "name": name,
                "opened": opened,
                "closed": closed,
                "link": link,
                "done": completion.get(link),
            })

    return {
        "linked": True,
        "courses": out_courses,
        "assignments": assignments,
        "exams": exams,
        "fetched_at": int(time.time()),
    }


class Handler(BaseHTTPRequestHandler):

    server_version = "NexisWeb/1.0"

    def log_message(self, fmt, *args):
        _LOG.info("%s - %s", self.address_string(), fmt % args)

    def send_json(self, status, data):
        body = _json(data)

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.send_header(
            "Cache-Control",
            "no-store",
        )
        self.send_header(
            "Access-Control-Allow-Origin",
            os.environ.get("WEB_CORS_ORIGIN", "*"),
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization, Content-Type",
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )
        self.end_headers()

        self.wfile.write(body)

    def error(self, status, message):
        self.send_json(status, {"error": message})

    def auth(self):
        uid = _read_token(self.headers.get("Authorization"))

        if uid is None:
            self.error(401, "unauthorized")
            return None

        return uid

    def body(self):
        length = min(
            int(self.headers.get("Content-Length", "0") or 0),
            128 * 1024,
        )

        raw = self.rfile.read(length)

        if not raw:
            return {}

        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self):
        self.send_json(204, {})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/health":
            self.send_json(
                200,
                {
                    "ok": True,
                    "maintenance": bool(
                        _BACKEND.is_maintenance()
                    ),
                },
            )
            return

        if path == "/api/me":
            uid = self.auth()

            if uid is None:
                return

            row = _user(uid)

            self.send_json(
                200,
                {
                    "telegram_id": uid,
                    "moodle_linked": bool(row),
                    "is_admin": bool(
                        _BACKEND.is_admin(uid)
                    ),
                },
            )
            return

        if path == "/api/updates":
            uid = self.auth()

            if uid is None:
                return

            limit = min(
                max(
                    int(query.get("limit", ["20"])[0]),
                    1,
                ),
                50,
            )

            with _BACKEND.db() as conn:
                rows = conn.execute(
                    """
                    SELECT course,name,link,first_seen
                    FROM material_log
                    WHERE telegram_id=?
                    ORDER BY first_seen DESC
                    LIMIT ?
                    """,
                    (uid, limit),
                ).fetchall()

            self.send_json(
                200,
                {
                    "items": [dict(row) for row in rows]
                },
            )
            return

        if path == "/api/library/search":
            uid = self.auth()

            if uid is None:
                return

            q = query.get("q", [""])[0].strip()

            if len(q) < 2:
                self.error(400, "query_too_short")
                return

            try:
                parsed_query = _BACKEND.parse_library_query(q)

                results = _BACKEND.search_indexed(
                    parsed_query,
                    limit=min(
                        getattr(
                            _BACKEND,
                            "ARCHIVE_SEARCH_LIMIT",
                            50,
                        ),
                        50,
                    ),
                )

                if results is None:
                    results, _ = asyncio.run(
                        _BACKEND.gather_library_results(
                            q,
                            parsed_query,
                        )
                    )

                items = []

                for item in results:
                    date = item.get("date")

                    items.append(
                        {
                            "chat": item.get("chat", ""),
                            "msg_id": int(
                                item.get("msg_id", 0)
                            ),
                            "name": item.get("name", ""),
                            "size_mb": round(
                                float(
                                    item.get(
                                        "size_mb",
                                        0,
                                    )
                                ),
                                2,
                            ),
                            "kind": item.get("kind"),
                            "date": (
                                date.isoformat()
                                if date
                                else None
                            ),
                            "caption": (
                                item.get("caption")
                                or item.get("post_text")
                                or ""
                            ),
                        }
                    )

                self.send_json(
                    200,
                    {"items": items},
                )

            except Exception as exc:
                _LOG.warning(
                    "library search failed: %s",
                    type(exc).__name__,
                )

                self.error(
                    503,
                    "library_unavailable",
                )

            return

        if path == "/api/moodle/overview":
            uid = self.auth()

            if uid is None:
                return

            self.send_json(
                200,
                _overview(
                    uid,
                    fresh=query.get("fresh", ["0"])[0] == "1",
                ),
            )
            return

        self.error(404, "not_found")

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/auth/telegram":
            try:
                data = self.body()

                if not _telegram_valid(data):
                    self.error(
                        401,
                        "invalid_telegram_auth",
                    )
                    return

                uid = int(data["id"])

                _BACKEND.track_user(uid)

                self.send_json(
                    200,
                    {
                        "token": _make_token(uid),
                        "expires_in": TOKEN_TTL,
                    },
                )

            except Exception:
                self.error(
                    400,
                    "invalid_request",
                )

            return

        if path == "/api/auth/logout":
            self.send_json(
                200,
                {"ok": True},
            )
            return

        if path == "/api/ai/ask":
            uid = self.auth()

            if uid is None:
                return

            try:
                data = self.body()

                question = str(
                    data.get("question", "")
                ).strip()

                if not question or len(question) > 4000:
                    self.error(
                        400,
                        "invalid_question",
                    )
                    return

                route = _BACKEND.fast_route(question)

                if route and route.get("mode") == "local":
                    answer = route.get(
                        "reply",
                        "",
                    )
                else:
                    answer = _BACKEND.assistant_generate(
                        route
                        or {
                            "mode": "concept"
                        },
                        question,
                        question,
                        None,
                        [],
                    )

                self.send_json(
                    200,
                    {
                        "answer": answer,
                        "remaining": None,
                    },
                )

            except Exception as exc:
                _LOG.warning(
                    "AI request failed: %s",
                    type(exc).__name__,
                )

                self.error(
                    502,
                    "ai_unavailable",
                )

            return

        self.error(404, "not_found")


async def start_web(backend):
    global _BACKEND
    global _SERVER
    global _THREAD

    _BACKEND = backend

    if _SERVER is not None:
        return

    host = os.environ.get(
        "WEB_HOST",
        "0.0.0.0",
    )

    port = int(
        os.environ.get(
            "PORT",
            os.environ.get(
                "WEB_PORT",
                "8787",
            ),
        )
    )

    _SERVER = ThreadingHTTPServer(
        (host, port),
        Handler,
    )

    _THREAD = threading.Thread(
        target=_SERVER.serve_forever,
        name="nexis-web",
        daemon=True,
    )

    _THREAD.start()

    _LOG.info(
        "Nexis Web API listening on %s:%s",
        host,
        port,
    )
