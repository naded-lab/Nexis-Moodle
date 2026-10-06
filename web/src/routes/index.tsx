import { createFileRoute, Link } from "@tanstack/react-router";
import { GraduationCap, BookOpen, Sparkles, Target, CalendarDays, Bell, TrendingUp, Zap, ArrowLeft, FileText, ClipboardList } from "lucide-react";
import { AppShell, useMe } from "@/components/AppShell";
import { Card, ErrorState, LoadingState } from "@/components/states";
import { DataView, Row } from "@/components/DataView";
import { useOverview, useUpdates, relDay, upcoming } from "@/lib/nexis-hooks";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Nexis Moodle — لوحتك الأكاديمية" },
      { name: "description", content: "واجباتك وامتحاناتك ومحاضراتك ومكتبتك ومساعدك الذكي في مكان واحد." },
      { property: "og:title", content: "Nexis Moodle — لوحتك الأكاديمية" },
      { property: "og:description", content: "منصة Nexis الأكاديمية: Moodle، المكتبة، والمساعد الذكي." },
    ],
  }),
  component: Dashboard,
});

const greeting = () => (new Date().getHours() < 12 ? "صباح الخير" : "مساء الخير");

const quick = [
  { to: "/moodle", label: "تصفح Moodle", sub: "المقررات والواجبات", icon: GraduationCap },
  { to: "/library", label: "ابحث في المكتبة", sub: "الملفات والمواد", icon: BookOpen },
  { to: "/assistant", label: "اسأل Nexis", sub: "المساعد الذكي", icon: Sparkles },
] as const;

function Stat({ n, label, icon, tone }: { n: number | string; label: string; icon: React.ReactNode; tone: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-card px-4 py-3 shadow-card">
      <div className={`grid h-10 w-10 place-items-center rounded-xl ${tone}`}>{icon}</div>
      <div><div className="text-lg font-bold leading-none">{n}</div><div className="mt-1 text-xs text-muted-foreground">{label}</div></div>
    </div>
  );
}

function Dashboard() {
  const me = useMe();
  const signed = !!me.data;
  const ov = useOverview(signed && !!me.data?.moodle_linked);
  const up = useUpdates(signed);
  const d = ov.data?.data;
  const nextAssign = d ? upcoming(d.assignments, (a) => a.due_ts).filter((a) => !a.done) : [];
  const nextExams = d ? upcoming(d.exams, (e) => e.close_ts ?? e.open_ts) : [];
  const all = d ? [...d.assignments, ...d.exams].filter((x) => x.done !== null) : [];
  const done = all.filter((x) => x.done).length;

  return (
    <AppShell>
      {me.isLoading ? (
        <LoadingState />
      ) : me.isError ? (
        <Card><ErrorState onRetry={() => me.refetch()} /></Card>
      ) : !me.data ? (
        <section className="rounded-3xl bg-hero p-8 sm:p-12">
          <h1 className="text-3xl font-bold sm:text-4xl">أهلاً بك في Nexis 👋</h1>
          <p className="mt-3 max-w-lg text-muted-foreground">سجّل الدخول بحساب تيليجرام نفسه الذي تستخدمه مع البوت، لتظهر واجباتك وامتحاناتك ومكتبتك هنا.</p>
          <Link to="/login" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 font-medium text-primary-foreground">
            تسجيل الدخول عبر تيليجرام <ArrowLeft className="h-4 w-4" />
          </Link>
        </section>
      ) : (
        <div className="grid gap-5 xl:grid-cols-3">
          <section className="rounded-3xl bg-hero p-6 sm:p-8 xl:col-span-2">
            <h1 className="text-2xl font-bold sm:text-3xl">مرحباً {me.data.first_name || me.data.username} 👋</h1>
            <p className="mt-2 text-muted-foreground">{greeting()}، هذه أهم ما لديك اليوم.</p>
            {!me.data.moodle_linked ? (
              <p className="mt-4 rounded-xl bg-card/70 px-4 py-3 text-sm">لم يتم ربط حساب Moodle بعد. اربطه من بوت تيليجرام ثم حدّث الصفحة.</p>
            ) : d ? (
              <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Stat n={nextAssign.length} label="مهام قادمة" icon={<FileText className="h-5 w-5" />} tone="bg-success-soft text-success" />
                <Stat n={d.courses.length} label="مقررات" icon={<GraduationCap className="h-5 w-5" />} tone="bg-primary-soft text-primary" />
                <Stat n={nextExams.length} label="امتحانات قريبة" icon={<CalendarDays className="h-5 w-5" />} tone="bg-violet-soft text-violet" />
              </div>
            ) : ov.isLoading ? (
              <p className="mt-4 text-sm text-muted-foreground">جاري جلب بياناتك من Moodle...</p>
            ) : null}
          </section>

          <Card title="آخر التحديثات" icon={<Bell className="h-5 w-5" />}>
            <DataView q={up} empty={(x) => x.items.length === 0}>
              {(x) => x.items.slice(0, 5).map((u, i) => <Row key={i} title={u.name} sub={u.course} href={u.link ?? undefined} icon={<BookOpen className="h-4 w-4" />} />)}
            </DataView>
          </Card>

          <Card title="ماذا تريد أن تفعل؟" icon={<Zap className="h-5 w-5" />} className="xl:col-span-2">
            <div className="grid gap-3 sm:grid-cols-3">
              {quick.map((q) => (
                <Link key={q.to} to={q.to} className="rounded-2xl border p-4 text-center hover:border-primary hover:bg-primary-soft">
                  <q.icon className="mx-auto h-7 w-7 text-primary" />
                  <div className="mt-2 font-semibold">{q.label}</div>
                  <div className="text-xs text-muted-foreground">{q.sub}</div>
                </Link>
              ))}
            </div>
          </Card>

          <Card title="تقدمك" icon={<TrendingUp className="h-5 w-5" />}>
            {me.data.moodle_linked && (
              <DataView q={ov} empty={() => all.length === 0}>
                {() => (
                  <div>
                    <div className="flex justify-between text-sm"><span>الأنشطة المكتملة</span><span dir="ltr">{done} / {all.length}</span></div>
                    <div className="mt-2 h-2.5 rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${(done / all.length) * 100}%` }} /></div>
                  </div>
                )}
              </DataView>
            )}
          </Card>

          {me.data.moodle_linked && (
            <>
              <Card title="الأولويات الحالية" icon={<Target className="h-5 w-5" />}>
                <DataView q={ov} empty={() => nextAssign.length === 0}>
                  {() => nextAssign.slice(0, 4).map((a, i) => <Row key={i} title={a.name} sub={a.course} side={relDay(a.due_ts)} href={a.link} icon={<ClipboardList className="h-4 w-4" />} />)}
                </DataView>
              </Card>
              <Card title="الامتحانات القادمة" icon={<CalendarDays className="h-5 w-5" />} className="xl:col-span-2">
                <DataView q={ov} empty={() => nextExams.length === 0}>
                  {() => nextExams.slice(0, 4).map((e, i) => <Row key={i} title={e.name} sub={e.course} side={relDay(e.close_ts ?? e.open_ts)} href={e.link} icon={<CalendarDays className="h-4 w-4" />} />)}
                </DataView>
              </Card>
            </>
          )}
        </div>
      )}
    </AppShell>
  );
}
