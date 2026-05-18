"use client";

import type { ActionItem } from "@/lib/api";
import ActionItemCard from "@/components/ActionItem";

interface ActionListProps {
  actions: ActionItem[];
}

interface SectionProps {
  title: string;
  dot: string;
  actions: ActionItem[];
}

function Section({ title, dot, actions }: SectionProps) {
  if (actions.length === 0) return null;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${dot}`} />
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">{title}</h2>
        <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-xs text-zinc-500">{actions.length}</span>
      </div>
      <div className="flex flex-col gap-2">
        {actions.map((action) => (
          <ActionItemCard key={action.title} action={action} />
        ))}
      </div>
    </div>
  );
}

export default function ActionList({ actions }: ActionListProps) {
  const critical = actions.filter((a) => a.priority === "critical");
  const important = actions.filter((a) => a.priority === "important");
  const improvement = actions.filter((a) => a.priority === "improvement");

  return (
    <div className="flex flex-col gap-8">
      <Section title="Hemen Yap" dot="bg-red-500" actions={critical} />
      <Section title="Bu Hafta Yap" dot="bg-amber-500" actions={important} />
      <Section title="İyileştir" dot="bg-emerald-500" actions={improvement} />
    </div>
  );
}
