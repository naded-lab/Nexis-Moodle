import { useQuery } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { getOverview, getUpdates } from "./nexis.functions";

export function useOverview(enabled: boolean) {
  const fn = useServerFn(getOverview);
  return useQuery({ queryKey: ["overview"], queryFn: () => fn({ data: {} }), enabled, staleTime: 120_000 });
}
export function useUpdates(enabled: boolean) {
  const fn = useServerFn(getUpdates);
  return useQuery({ queryKey: ["updates"], queryFn: () => fn(), enabled, staleTime: 60_000 });
}

const now = () => Date.now() / 1000;
export function relDay(ts: number | null) {
  if (!ts) return "بدون موعد";
  const d = Math.floor((ts - now()) / 86400);
  if (ts < now()) return "انتهى";
  if (d === 0) return "اليوم";
  if (d === 1) return "غداً";
  return `خلال ${d} أيام`;
}
export function upcoming<T>(items: T[], ts: (x: T) => number | null) {
  return items.filter((x) => (ts(x) ?? 0) > now()).sort((a, b) => (ts(a) ?? 0) - (ts(b) ?? 0));
}
