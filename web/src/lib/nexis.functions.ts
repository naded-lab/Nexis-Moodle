import { createServerFn } from "@tanstack/react-start";
import { getCookie, setCookie, deleteCookie } from "@tanstack/react-start/server";
import { z } from "zod";

const COOKIE = "nexis_session";

function base() {
  return (process.env["NEXIS_API_BASE_URL"] || "https://nexis.wisp.uno").replace(/\/$/, "");
}

async function call(path: string, init: RequestInit = {}, token?: string) {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${base()}${path}`, { ...init, headers });
  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  return { status: res.status, ok: res.ok, body };
}

export type Health = { ok: boolean; maintenance: boolean };
export type Me = {
  telegram_id: number;
  first_name?: string;
  username?: string;
  photo_url?: string;
  moodle_linked: boolean;
  is_admin: boolean;
};

export const getHealth = createServerFn({ method: "GET" }).handler(async (): Promise<Health> => {
  try {
    const r = await call("/api/health");
    if (!r.ok) return { ok: false, maintenance: false };
    return r.body as Health;
  } catch {
    return { ok: false, maintenance: false };
  }
});

export const getMe = createServerFn({ method: "GET" }).handler(async (): Promise<Me | null> => {
  const token = getCookie(COOKIE);
  if (!token) return null;
  const r = await call("/api/me", {}, token);
  if (r.status === 401) {
    deleteCookie(COOKIE);
    return null;
  }
  if (!r.ok) throw new Error("تعذر الاتصال بالخادم.");
  return r.body as Me;
});

const tgSchema = z.object({
  id: z.number(),
  first_name: z.string().max(256).optional(),
  last_name: z.string().max(256).optional(),
  username: z.string().max(64).optional(),
  photo_url: z.string().max(1024).optional(),
  auth_date: z.number(),
  hash: z.string().max(128),
});

export const telegramLogin = createServerFn({ method: "POST" })
  .inputValidator((d) => tgSchema.parse(d))
  .handler(async ({ data }) => {
    const r = await call("/api/auth/telegram", { method: "POST", body: JSON.stringify(data) });
    if (!r.ok) {
      const msg =
        r.status === 404
          ? "خدمة تسجيل الدخول غير مفعّلة على الخادم بعد."
          : "فشل التحقق من حساب تيليجرام.";
      return { ok: false as const, error: msg };
    }
    const { token, expires_in } = r.body as { token: string; expires_in: number };
    setCookie(COOKIE, token, {
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
      maxAge: expires_in || 60 * 60 * 24 * 30,
    });
    return { ok: true as const };
  });

export const logout = createServerFn({ method: "POST" }).handler(async () => {
  const token = getCookie(COOKIE);
  if (token) {
    try {
      await call("/api/auth/logout", { method: "POST" }, token);
    } catch {
      /* ignore */
    }
  }
  deleteCookie(COOKIE);
  return { ok: true };
});

// ---------- Data endpoints (all require the session cookie) ----------
export type Assignment = { course: string; name: string; opened: string; due: string; due_ts: number | null; link: string; done: boolean | null };
export type Exam = { course: string; name: string; opened: string; closed: string; open_ts: number | null; close_ts: number | null; link: string; done: boolean | null };
export type Overview = { linked: boolean; courses: { name: string; url: string; materials?: number; error?: boolean }[]; assignments: Assignment[]; exams: Exam[]; fetched_at?: number };
export type Result<T> = { data: T; error: null } | { data: null; error: string };

const ERR: Record<number, string> = {
  401: "انتهت الجلسة، سجّل الدخول من جديد.",
  404: "هذه الخدمة غير مفعّلة على الخادم بعد.",
  409: "يحتاج حساب Moodle إلى تسجيل دخول جديد من البوت.",
  429: "وصلت الحد اليومي لاستخدام المساعد الذكي.",
  502: "تعذر الاتصال بـ Moodle حالياً.",
  503: "فهرس المكتبة غير متاح حالياً.",
};

async function authed<T>(path: string, init: RequestInit = {}): Promise<Result<T>> {
  const token = getCookie(COOKIE);
  if (!token) return { data: null, error: ERR[401]! };
  try {
    const r = await call(path, init, token);
    if (!r.ok) return { data: null, error: ERR[r.status] ?? "تعذر الاتصال بالخادم." };
    return { data: r.body as T, error: null };
  } catch {
    return { data: null, error: "تعذر الاتصال بالخادم." };
  }
}

export const getOverview = createServerFn({ method: "GET" })
  .inputValidator((d: { fresh?: boolean } | undefined) => d ?? {})
  .handler(({ data }) => authed<Overview>(`/api/moodle/overview${data.fresh ? "?fresh=1" : ""}`));

export type Update = { course: string; name: string; link: string | null; first_seen: string };
export const getUpdates = createServerFn({ method: "GET" }).handler(() => authed<{ items: Update[] }>("/api/updates?limit=20"));

export type LibItem = { chat: string; msg_id: number; name: string; size_mb: number; kind: string | null; date: string | null; caption: string };
export const searchLibrary = createServerFn({ method: "GET" })
  .inputValidator((d) => z.object({ q: z.string().min(2).max(200) }).parse(d))
  .handler(({ data }) => authed<{ items: LibItem[] }>(`/api/library/search?q=${encodeURIComponent(data.q)}`));

export const askAI = createServerFn({ method: "POST" })
  .inputValidator((d) => z.object({ question: z.string().min(1).max(4000) }).parse(d))
  .handler(({ data }) =>
    authed<{ answer: string; remaining: number | null }>("/api/ai/ask", { method: "POST", body: JSON.stringify(data) }),
  );
