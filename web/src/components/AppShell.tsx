import { Link, useRouter } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { Home, Sparkles, BookOpen, GraduationCap, BarChart3, Bell, Settings, Search, LogOut, ShieldCheck, AlertTriangle } from "lucide-react";
import type { ReactNode } from "react";
import { getHealth, getMe, logout } from "@/lib/nexis.functions";

const nav = [
  { to: "/", label: "الرئيسية", icon: Home },
  { to: "/assistant", label: "المساعد الذكي", icon: Sparkles },
  { to: "/library", label: "المكتبة", icon: BookOpen },
  { to: "/moodle", label: "Moodle", icon: GraduationCap },
  { to: "/progress", label: "التقدم", icon: BarChart3 },
  { to: "/notifications", label: "الإشعارات", icon: Bell },
  { to: "/settings", label: "الإعدادات", icon: Settings },
] as const;

const mobileNav = [nav[0], nav[1], nav[2], nav[3], nav[5]] as const;

export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="grid h-10 w-10 place-items-center rounded-xl bg-brand text-xl font-black text-primary-foreground">N</div>
      <div className="leading-tight">
        <div className="text-xl font-bold">Nexis</div>
        <div className="text-[10px] text-muted-foreground" dir="ltr">AI Academic Platform</div>
      </div>
    </div>
  );
}

export function useMe() {
  const fn = useServerFn(getMe);
  return useQuery({ queryKey: ["me"], queryFn: () => fn(), retry: false });
}

export function useHealth() {
  const fn = useServerFn(getHealth);
  return useQuery({ queryKey: ["health"], queryFn: () => fn(), refetchInterval: 60_000 });
}

function UserMenu() {
  const me = useMe();
  const qc = useQueryClient();
  const router = useRouter();
  const out = useServerFn(logout);
  if (!me.data)
    return (
      <Link to="/login" className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
        تسجيل الدخول
      </Link>
    );
  const name = me.data.first_name || me.data.username || "طالب";
  return (
    <div className="flex items-center gap-2 rounded-full border bg-card py-1 pe-1 ps-3">
      <span className="hidden text-sm font-medium sm:inline">{name}</span>
      {me.data.is_admin && <ShieldCheck className="h-4 w-4 text-primary" aria-label="مشرف" />}
      <button
        onClick={async () => {
          await qc.cancelQueries();
          await out();
          qc.clear();
          router.navigate({ to: "/login", replace: true });
        }}
        className="grid h-8 w-8 place-items-center rounded-full bg-primary text-primary-foreground"
        aria-label="تسجيل الخروج"
        title="تسجيل الخروج"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}

function StatusBadge() {
  const h = useHealth();
  const online = h.data?.ok;
  return (
    <span className="hidden items-center gap-1.5 rounded-full border bg-card px-3 py-1.5 text-xs text-muted-foreground md:inline-flex">
      <span className={`h-2 w-2 rounded-full ${h.isLoading ? "bg-muted-foreground" : online ? "bg-success" : "bg-destructive"}`} />
      {h.isLoading ? "جاري الفحص" : online ? "الخادم متصل" : "الخادم غير متاح"}
    </span>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const h = useHealth();
  return (
    <div className="flex min-h-screen w-full">
      {/* Sidebar: first child in RTL flex = right side */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-e bg-card px-4 py-6 lg:flex">
        <div className="px-2"><Logo /></div>
        <nav className="mt-8 flex flex-col gap-1">
          {nav.map((n) => (
            <Link
              key={n.to}
              to={n.to}
              activeOptions={{ exact: n.to === "/" }}
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-foreground/80 hover:bg-muted"
              activeProps={{ className: "bg-primary-soft font-semibold text-accent-foreground" }}
            >
              <n.icon className="h-5 w-5 shrink-0" />
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto rounded-2xl bg-hero p-4 text-center">
          <div className="text-sm font-semibold">معاً نحو مستقبلك الأفضل</div>
          <div className="mt-1 text-xs text-muted-foreground">Nexis - منصة الذكاء الاصطناعي الأكاديمية</div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-b bg-background/85 px-4 py-3 backdrop-blur sm:px-6">
          <div className="lg:hidden"><Logo /></div>
          <label className="col-start-2 hidden max-w-xl items-center gap-2 rounded-xl border bg-card px-3 py-2 text-sm text-muted-foreground sm:flex lg:col-start-1 lg:col-span-2">
            <Search className="h-4 w-4 shrink-0" />
            <input className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted-foreground" placeholder="ابحث في كل ما تحتاجه..." />
          </label>
          <div className="col-start-3 flex items-center gap-2">
            <StatusBadge />
            <UserMenu />
          </div>
        </header>

        {h.data?.maintenance && (
          <div className="flex items-center gap-2 bg-warning-soft px-6 py-2 text-sm text-foreground">
            <AlertTriangle className="h-4 w-4 text-warning" /> المنصة في وضع الصيانة حالياً، قد تكون بعض الخدمات غير متاحة.
          </div>
        )}

        <main className="flex-1 px-4 pb-24 pt-6 sm:px-6 lg:pb-8">{children}</main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t bg-card pb-[env(safe-area-inset-bottom)] lg:hidden">
        {mobileNav.map((n) => (
          <Link
            key={n.to}
            to={n.to}
            activeOptions={{ exact: n.to === "/" }}
            className="flex flex-col items-center gap-1 py-2 text-[11px] text-muted-foreground"
            activeProps={{ className: "text-primary font-semibold" }}
          >
            <n.icon className="h-5 w-5" />
            {n.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
