import type { ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import type { Result } from "@/lib/nexis.functions";
import { EmptyState, ErrorState, LoadingState } from "./states";

/** Renders loading / error / empty / data states for a Result<T> query. */
export function DataView<T>({ q, empty, children }: { q: UseQueryResult<Result<T>>; empty?: (d: T) => boolean; children: (d: T) => ReactNode }) {
  if (q.isLoading) return <LoadingState />;
  if (q.isError) return <ErrorState onRetry={() => q.refetch()} />;
  const r = q.data;
  if (!r) return <LoadingState />;
  if (r.error !== null) return <ErrorState text={r.error} onRetry={() => q.refetch()} />;
  if (empty?.(r.data)) return <EmptyState />;
  return <>{children(r.data)}</>;
}

export function Row({ title, sub, side, href, icon }: { title: string; sub?: string | undefined; side?: string | undefined; href?: string | undefined; icon?: ReactNode }) {
  const body = (
    <div className="flex min-w-0 items-center gap-3 py-3">
      {icon && <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary-soft text-primary">{icon}</div>}
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">{title}</div>
        {sub && <div className="truncate text-xs text-muted-foreground">{sub}</div>}
      </div>
      {side && <div className="shrink-0 text-xs text-muted-foreground">{side}</div>}
    </div>
  );
  return href ? <a href={href} target="_blank" rel="noreferrer" className="block border-b last:border-0 hover:bg-muted/50">{body}</a> : <div className="border-b last:border-0">{body}</div>;
}
