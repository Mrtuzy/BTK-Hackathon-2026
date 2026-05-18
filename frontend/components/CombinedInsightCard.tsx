"use client";

import type { ActionItem } from "@/lib/api";

interface CombinedInsightCardProps {
  insight: string;
  actions: ActionItem[];
}

export default function CombinedInsightCard({ insight, actions }: CombinedInsightCardProps) {
  const critical = actions.filter((a) => a.priority === "critical").length;
  const important = actions.filter((a) => a.priority === "important").length;
  const improvement = actions.filter((a) => a.priority === "improvement").length;

  return (
    <div className="relative overflow-hidden rounded-2xl">
      {/* Gradient border layer */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-violet-600/60 via-cyan-500/30 to-violet-600/50" />
      {/* Inner card */}
      <div className="relative m-px rounded-2xl bg-zinc-900 p-6">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-cyan-500">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">Birleşik Analiz</p>
              <p className="text-sm font-semibold text-zinc-100">Genel Kâr Durumu</p>
            </div>
          </div>
          <span className="shrink-0 rounded-full border border-zinc-700 bg-zinc-800/80 px-2.5 py-1 text-xs text-zinc-500">
            AI tarafından üretildi
          </span>
        </div>

        <div className="border-l-2 border-violet-500/60 pl-4">
          <p className="text-sm leading-relaxed text-zinc-200">{insight}</p>
        </div>

        {(critical > 0 || important > 0 || improvement > 0) && (
          <div className="mt-5 flex flex-wrap gap-2">
            {critical > 0 && (
              <span className="flex items-center gap-1.5 rounded-full bg-red-500/10 px-3 py-1 text-xs font-medium text-red-400 ring-1 ring-red-500/20">
                <div className="h-1.5 w-1.5 rounded-full bg-red-500" />
                {critical} kritik aksiyon
              </span>
            )}
            {important > 0 && (
              <span className="flex items-center gap-1.5 rounded-full bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-400 ring-1 ring-amber-500/20">
                <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                {important} önemli aksiyon
              </span>
            )}
            {improvement > 0 && (
              <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400 ring-1 ring-emerald-500/20">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {improvement} iyileştirme
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
