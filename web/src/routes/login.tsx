import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { useQueryClient } from "@tanstack/react-query";
import { telegramLogin } from "@/lib/nexis.functions";
import { Logo } from "@/components/AppShell";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "تسجيل الدخول — Nexis Moodle" },
      { name: "description", content: "سجّل الدخول إلى Nexis بحساب تيليجرام." },
      { property: "og:title", content: "تسجيل الدخول — Nexis Moodle" },
      { property: "og:description", content: "هوية واحدة بين بوت تيليجرام والموقع." },
    ],
  }),
  component: Login,
});

const BOT = "NexisMBot";

function Login() {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const login = useServerFn(telegramLogin);
  const qc = useQueryClient();
  const navigate = useNavigate();

  useEffect(() => {
    if (!BOT || !ref.current) return;
    (window as unknown as Record<string, unknown>)['onNexisTelegramAuth'] = async (user: Record<string, unknown>) => {
      setBusy(true);
      setError(null);
      try {
        const r = await login({ data: user as never });
        if (!r.ok) setError(r.error);
        else {
          await qc.invalidateQueries({ queryKey: ["me"] });
          navigate({ to: "/" });
        }
      } catch {
        setError("تعذر الاتصال بالخادم.");
      } finally {
        setBusy(false);
      }
    };
    const s = document.createElement("script");
    s.src = "https://telegram.org/js/telegram-widget.js?22";
    s.async = true;
    s.setAttribute("data-telegram-login", BOT);
    s.setAttribute("data-size", "large");
    s.setAttribute("data-radius", "12");
    s.setAttribute("data-lang", "ar");
    s.setAttribute("data-request-access", "write");
    s.setAttribute("data-onauth", "onNexisTelegramAuth(user)");
    ref.current.innerHTML = "";
    ref.current.appendChild(s);
  }, [login, qc, navigate]);

  return (
    <div className="grid min-h-screen place-items-center bg-hero px-4">
      <div className="w-full max-w-sm rounded-3xl border bg-card p-8 text-center shadow-card">
        <div className="flex justify-center"><Logo /></div>
        <h1 className="mt-6 text-xl font-bold">تسجيل الدخول</h1>
        <p className="mt-2 text-sm text-muted-foreground">استخدم حساب تيليجرام نفسه المرتبط ببوت Nexis.</p>
        <div ref={ref} className="mt-6 flex min-h-12 justify-center" />
        {!BOT && <p className="mt-2 text-sm text-destructive">لم يتم ضبط اسم البوت بعد.</p>}
        {busy && <p className="mt-3 text-sm text-muted-foreground">جاري التحقق...</p>}
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </div>
    </div>
  );
}
