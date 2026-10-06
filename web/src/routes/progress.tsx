import { createFileRoute } from "@tanstack/react-router";
import { BarChart3 } from "lucide-react";
import { SectionPage } from "@/components/ComingFromServer";

export const Route = createFileRoute("/progress")({
  head: () => ({
    meta: [
      { title: "التقدم — Nexis Moodle" },
      { name: "description", content: "التقدم في منصة Nexis الأكاديمية." },
      { property: "og:title", content: "التقدم — Nexis Moodle" },
      { property: "og:description", content: "التقدم في منصة Nexis الأكاديمية." },
    ],
  }),
  component: () => <SectionPage title="التقدم" icon={<BarChart3 className="h-6 w-6" />} endpoint="/api/progress" />,
});
