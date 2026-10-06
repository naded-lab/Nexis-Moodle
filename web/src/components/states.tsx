import { Loader2, CloudOff, Inbox, RotateCw } from "lucide-react";
import type { ReactNode } from "react";

export function LoadingState({ text = "جاري تحميل البيانات..." }: { text?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" /> {text}
    </div>
  );
}

export function EmptyState({ text = "لا توجد بيانات متاحة حالياً.", icon }: { text?: string; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-sm text-muted-foreground">
      <div className="grid h-11 w-11 place-items-center rounded-xl bg-muted">{icon ?? <Inbox className="h-5 w-5" />}</div>
      {text}
    </div>
  );
}

export function ErrorState({ text = "تعذر الاتصال بالخادم.", onRetry }: { text?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-10 text-center text-sm text-muted-foreground">
      <CloudOff className="h-6 w-6 text-destructive" />
      {text}
      {onRetry && (
        <button onClick={onRetry} className="inline-flex items-center gap-1.5 rounded-lg bg-primary-soft px-3 py-1.5 text-xs font-medium text-accent-foreground hover:bg-accent">
          <RotateCw className="h-3.5 w-3.5" /> إعادة المحاولة
        </button>
      )}
    </div>
  );
}

export function Card({ title, icon, children, className = "" }: { title?: string; icon?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border bg-card p-5 shadow-card ${className}`}>
      {title && (
        <h2 className="mb-3 flex items-center gap-2 text-base font-semibold">
          {icon && <span className="text-primary">{icon}</span>}
          {title}
        </h2>
      )}
      {children}
    </section>
  );
}
