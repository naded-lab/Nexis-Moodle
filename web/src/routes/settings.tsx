import { createFileRoute } from "@tanstack/react-router";
import { Settings } from "lucide-react";
import { SectionPage } from "@/components/ComingFromServer";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "الإعدادات — Nexis Moodle" },
      { name: "description", content: "الإعدادات في منصة Nexis الأكاديمية." },
      { property: "og:title", content: "الإعدادات — Nexis Moodle" },
      { property: "og:description", content: "الإعدادات في منصة Nexis الأكاديمية." },
    ],
  }),
  component: () => <SectionPage title="الإعدادات" icon={<Settings className="h-6 w-6" />} endpoint="/api/settings" />,
});
