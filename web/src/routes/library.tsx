import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { BookOpen, Search, FileText } from "lucide-react";
import { SectionPage } from "@/components/ComingFromServer";
import { DataView, Row } from "@/components/DataView";
import { EmptyState } from "@/components/states";
import { searchLibrary } from "@/lib/nexis.functions";

export const Route = createFileRoute("/library")({
  head: () => ({
    meta: [
      { title: "المكتبة — Nexis Moodle" },
      { name: "description", content: "ابحث في أرشيف ملفات ومواد Nexis." },
      { property: "og:title", content: "المكتبة — Nexis Moodle" },
      { property: "og:description", content: "ابحث في أرشيف ملفات ومواد Nexis." },
    ],
  }),
  component: LibraryPage,
});

function LibraryPage() {
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const fn = useServerFn(searchLibrary);
  const res = useQuery({ queryKey: ["library", q], queryFn: () => fn({ data: { q } }), enabled: q.length >= 2 });
  return (
    <SectionPage title="المكتبة" icon={<BookOpen className="h-6 w-6" />} endpoint="/api/library">
      <form onSubmit={(e) => { e.preventDefault(); setQ(text.trim()); }} className="mb-4 flex gap-2">
        <input value={text} onChange={(e) => setText(e.target.value)} maxLength={200} placeholder="اسم مادة، ملخص، رمز مقرر..." className="min-w-0 flex-1 rounded-xl border bg-background px-4 py-2.5 text-sm outline-none focus:border-primary" />
        <button className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-primary px-4 text-sm font-medium text-primary-foreground"><Search className="h-4 w-4" /> بحث</button>
      </form>
      {q.length < 2 ? (
        <EmptyState text="اكتب كلمة للبحث في المكتبة." icon={<Search className="h-5 w-5" />} />
      ) : (
        <DataView q={res} empty={(d) => d.items.length === 0}>
          {(d) => d.items.map((it) => (
            <Row key={`${it.chat}-${it.msg_id}`} title={it.name} sub={it.caption || it.kind || ""} side={`${it.size_mb} MB${it.date ? " · " + it.date : ""}`} icon={<FileText className="h-4 w-4" />} />
          ))}
        </DataView>
      )}
    </SectionPage>
  );
}
