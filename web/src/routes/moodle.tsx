import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { GraduationCap, ClipboardList, CalendarDays, BookOpen, CheckCircle2 } from "lucide-react";
import { SectionPage } from "@/components/ComingFromServer";
import { DataView, Row } from "@/components/DataView";
import { useMe } from "@/components/AppShell";
import { EmptyState } from "@/components/states";
import { useOverview, relDay } from "@/lib/nexis-hooks";

export const Route = createFileRoute("/moodle")({
  head: () => ({
    meta: [
      { title: "Moodle — Nexis Moodle" },
      { name: "description", content: "مقرراتك وواجباتك وامتحاناتك من Moodle." },
      { property: "og:title", content: "Moodle — Nexis Moodle" },
      { property: "og:description", content: "مقرراتك وواجباتك وامتحاناتك من Moodle." },
    ],
  }),
  component: MoodlePage,
});

const tabs = [
  { id: "assign", label: "الواجبات" },
  { id: "exams", label: "الامتحانات" },
  { id: "courses", label: "المقررات" },
] as const;

function MoodlePage() {
  const me = useMe();
  const ov = useOverview(!!me.data?.moodle_linked);
  const [tab, setTab] = useState<(typeof tabs)[number]["id"]>("assign");
  return (
    <SectionPage title="Moodle" icon={<GraduationCap className="h-6 w-6" />} endpoint="/api/moodle">
      {!me.data?.moodle_linked ? (
        <EmptyState text="لم يتم ربط حساب Moodle بعد. اربطه من بوت تيليجرام." />
      ) : (
        <>
          <div className="mb-3 flex gap-2 overflow-x-auto">
            {tabs.map((t) => (
              <button key={t.id} onClick={() => setTab(t.id)} className={`shrink-0 rounded-xl px-4 py-2 text-sm ${tab === t.id ? "bg-primary text-primary-foreground" : "bg-muted"}`}>{t.label}</button>
            ))}
          </div>
          <DataView q={ov}>
            {(d) => {
              const list =
                tab === "courses"
                  ? d.courses.map((c, i) => <Row key={i} title={c.name} sub={c.error ? "تعذر قراءة المقرر" : `${c.materials ?? 0} مادة`} href={c.url} icon={<BookOpen className="h-4 w-4" />} />)
                  : tab === "assign"
                    ? [...d.assignments].sort((a, b) => (a.due_ts ?? 9e12) - (b.due_ts ?? 9e12)).map((a, i) => (
                        <Row key={i} title={a.name} sub={`${a.course} · ${a.due || "بدون موعد"}`} side={a.done ? "مكتمل" : relDay(a.due_ts)} href={a.link} icon={a.done ? <CheckCircle2 className="h-4 w-4" /> : <ClipboardList className="h-4 w-4" />} />
                      ))
                    : [...d.exams].sort((a, b) => (a.close_ts ?? a.open_ts ?? 9e12) - (b.close_ts ?? b.open_ts ?? 9e12)).map((e, i) => (
                        <Row key={i} title={e.name} sub={`${e.course} · ${e.opened || "—"} ← ${e.closed || "—"}`} side={e.done ? "مكتمل" : relDay(e.close_ts ?? e.open_ts)} href={e.link} icon={<CalendarDays className="h-4 w-4" />} />
                      ));
              return list.length ? <div>{list}</div> : <EmptyState />;
            }}
          </DataView>
        </>
      )}
    </SectionPage>
  );
}
