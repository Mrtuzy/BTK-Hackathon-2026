"use client";

import { useState } from "react";
import type { KeywordRoiEntry } from "@/lib/api";

interface KeywordRoiTableProps {
  data: KeywordRoiEntry[];
}

type SortKey = "spend" | "efficiency_score" | "return_rate" | "ctr" | "conversion_rate";

function EfficiencyBar({ score }: { score: number }) {
  const color =
    score >= 70 ? "bg-emerald-500" : score >= 40 ? "bg-amber-500" : "bg-red-500";
  const textColor =
    score >= 70 ? "text-emerald-400" : score >= 40 ? "text-amber-400" : "text-red-400";
  return (
    <div className="flex items-center justify-end gap-2">
      <div className="h-1.5 w-14 overflow-hidden rounded-full bg-zinc-800">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${score}%` }} />
      </div>
      <span className={`w-7 text-right text-xs font-semibold tabular-nums ${textColor}`}>{score}</span>
    </div>
  );
}

function RateCell({ value, threshold1, threshold2 }: { value: number; threshold1: number; threshold2: number }) {
  const pct = (value * 100).toFixed(1);
  const color =
    value > threshold2 ? "text-red-400" : value > threshold1 ? "text-amber-400" : "text-emerald-400";
  return <span className={`tabular-nums ${color}`}>{pct}%</span>;
}

export default function KeywordRoiTable({ data }: KeywordRoiTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("spend");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  if (!data || data.length === 0) return null;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey] ?? 0;
    const bv = b[sortKey] ?? 0;
    return sortDir === "desc" ? (bv as number) - (av as number) : (av as number) - (bv as number);
  });

  const SortIcon = ({ k }: { k: SortKey }) => (
    <span className={`ml-1 text-zinc-600 ${sortKey === k ? "text-violet-400" : ""}`}>
      {sortKey === k ? (sortDir === "desc" ? "↓" : "↑") : "↕"}
    </span>
  );

  const thCls = "px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500 select-none";
  const thRCls = `${thCls} cursor-pointer text-right hover:text-zinc-300 transition-colors`;

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900">
      <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
        <div className="flex items-center gap-2.5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2">
            <line x1="12" y1="20" x2="12" y2="10" /><line x1="18" y1="20" x2="18" y2="4" />
            <line x1="6" y1="20" x2="6" y2="16" />
          </svg>
          <h3 className="text-sm font-semibold text-zinc-200">Anahtar Kelime ROI Haritası</h3>
        </div>
        <span className="rounded-full bg-zinc-800 px-2.5 py-1 text-xs text-zinc-500">
          {data.length} kelime
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-sm">
          <thead>
            <tr className="border-b border-zinc-800/80">
              <th className={thCls}>Kelime / Reklam</th>
              <th className={thRCls} onClick={() => handleSort("spend")}>
                Harcama <SortIcon k="spend" />
              </th>
              <th className={thRCls} onClick={() => handleSort("ctr")}>
                CTR <SortIcon k="ctr" />
              </th>
              <th className={thRCls} onClick={() => handleSort("conversion_rate")}>
                Dönüşüm <SortIcon k="conversion_rate" />
              </th>
              <th className={thRCls} onClick={() => handleSort("return_rate")}>
                İade % <SortIcon k="return_rate" />
              </th>
              <th className={thRCls} onClick={() => handleSort("efficiency_score")}>
                Verimlilik <SortIcon k="efficiency_score" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr
                key={i}
                className="border-b border-zinc-800/40 transition-colors hover:bg-zinc-800/30"
              >
                <td className="px-4 py-3">
                  <div>
                    <p className="font-medium text-zinc-200">{row.keyword}</p>
                    {row.cpa !== null && (
                      <p className="text-xs text-zinc-500">CPA: ₺{row.cpa.toLocaleString("tr-TR")}</p>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-zinc-300">
                  ₺{row.spend.toLocaleString("tr-TR", { maximumFractionDigits: 0 })}
                </td>
                <td className="px-4 py-3 text-right">
                  <RateCell value={row.ctr} threshold1={0.02} threshold2={0.01} />
                </td>
                <td className="px-4 py-3 text-right">
                  <RateCell value={row.conversion_rate} threshold1={0.03} threshold2={0.01} />
                </td>
                <td className="px-4 py-3 text-right">
                  <RateCell value={row.return_rate} threshold1={0.1} threshold2={0.3} />
                </td>
                <td className="px-4 py-3 text-right">
                  <EfficiencyBar score={row.efficiency_score} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-4 border-t border-zinc-800 px-5 py-3">
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-2 rounded-full bg-emerald-500" />
          <span className="text-xs text-zinc-500">Verimli (70+)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-2 rounded-full bg-amber-500" />
          <span className="text-xs text-zinc-500">Orta (40-69)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-2 rounded-full bg-red-500" />
          <span className="text-xs text-zinc-500">Verimsiz (&lt;40)</span>
        </div>
      </div>
    </div>
  );
}
