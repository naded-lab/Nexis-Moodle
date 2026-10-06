import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { AppShell, useMe } from "./AppShell";
import { Card, EmptyState, ErrorState, LoadingState } from "./states";

/** Page frame for sections whose server endpoints are not live yet. Shows real state only. */
export function SectionPage({ title, icon, endpoint, children }: { title: string; icon: ReactNode; endpoint: string; children?: ReactNode }) {
  const me = useMe();
  return (
    <AppShell>
      <h1 className="mb-5 flex items-center gap-2 text-2xl font-bold">
        <span className="text-primary">{icon}</span>
        {title}
      </h1>
      <Card>
        {me.isLoading ? (
          <LoadingState />
        ) : me.isError ? (
          <ErrorState onRetry={() => me.refetch()} />
        ) : !me.data ? (
          <div className="py-8 text-center">
            <p className="text-sm text-muted-foreground">سجّل الدخول لعرض بياناتك.</p>
            <Link to="/login" className="mt-4 inline-block rounded-xl bg-primary px-5 py-2 text-sm font-medium text-primary-foreground">تسجيل الدخول</Link>
          </div>
        ) : (
          children ?? (
            <EmptyState text={`هذا القسم سيعرض بياناتك فور تفعيل ${endpoint} على الخادم.`} icon={icon} />
          )
        )}
      </Card>
    </AppShell>
  );
}
