import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { Sparkles, Send, Loader2 } from "lucide-react";
import { SectionPage } from "@/components/ComingFromServer";
import { askAI } from "@/lib/nexis.functions";

export const Route = createFileRoute("/assistant")({
  head: () => ({
    meta: [
      { title: "المساعد الذكي — Nexis Moodle" },
      { name: "description", content: "اسأل مساعد Nexis الذكي عن أي شيء في دراستك." },
      { property: "og:title", content: "المساعد الذكي — Nexis Moodle" },
      { property: "og:description", content: "اسأل مساعد Nexis الذكي عن أي شيء في دراستك." },
    ],
  }),
  component: Assistant,
});

type Msg = { role: "user" | "ai" | "err"; text: string };

function Assistant() {
  const ask = useServerFn(askAI);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [left, setLeft] = useState<number | null>(null);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const q = text.trim();
    if (!q || busy) return;
    setText("");
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const r = await ask({ data: { question: q } });
      if (r.error !== null) setMsgs((m) => [...m, { role: "err", text: r.error }]);
      else {
        setMsgs((m) => [...m, { role: "ai", text: r.data.answer }]);
        setLeft(r.data.remaining);
      }
    } catch {
      setMsgs((m) => [...m, { role: "err", text: "تعذر الاتصال بالخادم." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <SectionPage title="المساعد الذكي" icon={<Sparkles className="h-6 w-6" />} endpoint="/api/ai">
      <div className="flex min-h-[50vh] flex-col">
        <div className="flex-1 space-y-3">
          {msgs.length === 0 && <p className="py-10 text-center text-sm text-muted-foreground">اسأل أي شيء، اشرح، لخّص، أو احصل على المساعدة في دراستك.</p>}
          {msgs.map((m, i) => (
            <div key={i} className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${m.role === "user" ? "ms-auto bg-primary text-primary-foreground" : m.role === "err" ? "bg-destructive/10 text-destructive" : "bg-muted"}`}>{m.text}</div>
          ))}
          {busy && <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> يفكر...</div>}
        </div>
        <form onSubmit={send} className="mt-4 flex gap-2">
          <textarea value={text} onChange={(e) => setText(e.target.value)} maxLength={4000} rows={1} placeholder="اكتب سؤالك..." className="min-w-0 flex-1 resize-none rounded-xl border bg-background px-4 py-2.5 text-sm outline-none focus:border-primary" />
          <button disabled={busy} className="grid w-12 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground disabled:opacity-50" aria-label="إرسال"><Send className="h-4 w-4 -scale-x-100" /></button>
        </form>
        {left !== null && <p className="mt-2 text-xs text-muted-foreground">المتبقي اليوم: {left}</p>}
      </div>
    </SectionPage>
  );
}
