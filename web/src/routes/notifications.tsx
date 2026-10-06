import { createFileRoute } from "@tanstack/react-router";
import { Bell } from "lucide-react";
import { SectionPage } from "@/components/ComingFromServer";

export const Route = createFileRoute("/notifications")({
  head: () => ({
    meta: [
      { title: "الإشعارات — Nexis Moodle" },
      { name: "description", content: "الإشعارات في منصة Nexis الأكاديمية." },
      { property: "og:title", content: "الإشعارات — Nexis Moodle" },
      { property: "og:description", content: "الإشعارات في منصة Nexis الأكاديمية." },
    ],
  }),
  component: () => <SectionPage title="الإشعارات" icon={<Bell className="h-6 w-6" />} endpoint="/api/notifications" />,
});
