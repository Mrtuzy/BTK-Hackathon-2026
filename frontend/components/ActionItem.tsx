"use client";

import { useEffect, useState } from "react";
import type { ActionItem as ActionItemType } from "@/lib/api";

interface ActionItemProps {
  action: ActionItemType;
}

const priorityConfig = {
  critical: {
    bar: "bg-red-500",
    badge: "bg-red-500/12 text-red-400 ring-1 ring-red-500/20",
    label: "Kritik",
    icon: (
      <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2L1 21h22L12 2zm0 3.5L20.5 19h-17L12 5.5zM11 10v4h2v-4h-2zm0 6v2h2v-2h-2z" />
      </svg>
    ),
  },
  important: {
    bar: "bg-amber-500",
    badge: "bg-amber-500/12 text-amber-400 ring-1 ring-amber-500/20",
    label: "Önemli",
    icon: (
      <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
        <circle cx="12" cy="12" r="10" opacity="0.3" />
        <path d="M12 7v6M12 17v.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
  },
  improvement: {
    bar: "bg-emerald-500",
    badge: "bg-emerald-500/12 text-emerald-400 ring-1 ring-emerald-500/20",
    label: "İyileştirme",
    icon: (
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" />
      </svg>
    ),
  },
} as const;

export default function ActionItem({ action }: ActionItemProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const t = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(t);
  }, [copied]);

  const cfg = priorityConfig[action.priority] ?? priorityConfig.improvement;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(`${action.title}\n\n${action.how_to_apply}`);
    setCopied(true);
  };

  return (
    <div className="group relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900 transition-all hover:border-zinc-700">
      <div className={`absolute left-0 top-0 h-full w-0.5 ${cfg.bar}`} />

      <div className="px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${cfg.badge}`}>
              {cfg.icon}
              {cfg.label}
            </span>
          </div>

          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium text-zinc-500 transition-all hover:bg-zinc-800 hover:text-zinc-300"
          >
            {copied ? (
              <>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span className="text-emerald-400">Kopyalandı</span>
              </>
            ) : (
              <>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                </svg>
                Kopyala
              </>
            )}
          </button>
        </div>

        <h3 className="mt-3 text-base font-semibold text-zinc-100">{action.title}</h3>
        <p className="mt-1.5 text-sm leading-relaxed text-zinc-400">{action.description}</p>

        <div className="mt-3 flex items-center gap-2">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
          <span className="text-xs font-medium text-violet-400">{action.estimated_impact}</span>
        </div>

        <button
          type="button"
          onClick={() => setIsOpen((o) => !o)}
          className="mt-4 flex items-center gap-2 text-xs font-medium text-zinc-500 transition-colors hover:text-zinc-300"
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className={`transition-transform ${isOpen ? "rotate-180" : ""}`}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
          Nasıl uygulanır?
        </button>

        {isOpen && (
          <div className="mt-3 rounded-lg border border-zinc-800 bg-zinc-950 p-3.5 text-sm leading-relaxed text-zinc-300">
            {action.how_to_apply}
          </div>
        )}
      </div>
    </div>
  );
}
