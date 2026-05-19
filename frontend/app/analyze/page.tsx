"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ActionList from "@/components/ActionList";
import CombinedInsightCard from "@/components/CombinedInsightCard";
import KeywordRoiTable from "@/components/KeywordRoiTable";
import MetricCard from "@/components/MetricCard";
import type { AnalyzeResponse } from "@/lib/api";

const AD_TYPE_LABELS: Record<string, string> = {
  video: "Video Reklamı",
  display: "Görüntülü Reklam",
  shopping: "Alışveriş Reklamı",
  search: "Arama Reklamı",
};

// ── Animated counter ──────────────────────────────────────────────────────────

function useCountUp(target: number, duration = 1200): number {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (target === 0) { setValue(0); return; }
    const start = performance.now();
    const raf = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(raf);
    };
    requestAnimationFrame(raf);
  }, [target, duration]);
  return value;
}

// ── Copy button ───────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      type="button"
      onClick={copy}
      title="Kopyala"
      className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-all ${
        copied
          ? "bg-emerald-500/15 text-emerald-400"
          : "bg-zinc-800 text-zinc-500 hover:bg-zinc-700 hover:text-zinc-300"
      }`}
    >
      {copied ? (
        <>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12" /></svg>
          Kopyalandı
        </>
      ) : (
        <>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" /></svg>
          Kopyala
        </>
      )}
    </button>
  );
}

// ── UI helpers ────────────────────────────────────────────────────────────────

function SectionHeader({ icon, title, badge }: { icon: React.ReactNode; title: string; badge?: string }) {
  return (
    <div className="mb-5 flex items-center gap-2.5">
      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-zinc-800">{icon}</div>
      <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">{title}</h2>
      {badge && <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-xs text-zinc-500">{badge}</span>}
    </div>
  );
}

function InsightCard({ title, children, accent, action }: {
  title: string; children: React.ReactNode; accent?: string; action?: React.ReactNode;
}) {
  return (
    <div className={`rounded-xl border ${accent ?? "border-zinc-800"} bg-zinc-900 p-5`}>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}

function KeywordBadge({ keyword, variant = "default" }: { keyword: string; variant?: "default" | "warning" | "danger" }) {
  const styles = {
    default: "border-violet-500/20 bg-violet-500/8 text-violet-300",
    warning: "border-amber-500/20 bg-amber-500/8 text-amber-300",
    danger: "border-red-500/20 bg-red-500/8 text-red-300",
  };
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${styles[variant]}`}>
      {keyword}
    </span>
  );
}

function FunnelRow({ result }: { result: AnalyzeResponse }) {
  if (!result.total_impressions && !result.total_clicks) return null;
  const items = [
    { label: "Gösterim", value: result.total_impressions, icon: "👁" },
    { label: "Tıklama", value: result.total_clicks, icon: "👆" },
    { label: "Dönüşüm", value: result.total_conversions, icon: "✓" },
    { label: "İade", value: result.total_returns, icon: "↩" },
  ];
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-zinc-500">Dönüşüm Hunisi</h3>
      <div className="flex flex-wrap items-center gap-2">
        {items.map((item, i) => {
          const prev = i > 0 ? items[i - 1].value : null;
          const rate = prev && prev > 0 ? ((item.value / prev) * 100).toFixed(1) : null;
          const rateColor =
            i === 3
              ? item.value / (items[2].value || 1) > 0.2 ? "text-red-400" : "text-emerald-400"
              : rate && parseFloat(rate) < 3 ? "text-red-400" : "text-zinc-500";
          return (
            <div key={item.label} className="flex items-center gap-2">
              {i > 0 && (
                <div className="flex flex-col items-center">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-zinc-700">
                    <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
                  </svg>
                  {rate && <span className={`text-xs tabular-nums ${rateColor}`}>{rate}%</span>}
                </div>
              )}
              <div className="flex flex-col items-center rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2">
                <span className="text-sm">{item.icon}</span>
                <span className="text-sm font-bold tabular-nums text-zinc-200">{item.value.toLocaleString("tr-TR")}</span>
                <span className="text-xs text-zinc-600">{item.label}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BudgetEfficiencyCard({ score, funnel_drop_points }: { score: number; funnel_drop_points: string[] }) {
  const animated = useCountUp(score);
  const color = score >= 70 ? "bg-emerald-500" : score >= 40 ? "bg-amber-500" : "bg-red-500";
  const textColor = score >= 70 ? "text-emerald-400" : score >= 40 ? "text-amber-400" : "text-red-400";
  const label = score >= 70 ? "Verimli" : score >= 40 ? "Orta" : "Verimsiz";
  return (
    <InsightCard title="Bütçe Verimlilik Skoru">
      <div className="flex items-end gap-4">
        <div>
          <p className={`text-4xl font-bold tabular-nums ${textColor}`}>{animated}</p>
          <p className="text-xs text-zinc-600">/100 · {label}</p>
        </div>
        <div className="flex-1 pb-1">
          <div className="mb-1 flex justify-between text-xs text-zinc-600"><span>0</span><span>50</span><span>100</span></div>
          <div className="h-2 overflow-hidden rounded-full bg-zinc-800">
            <div className={`h-full rounded-full ${color} transition-all duration-1000`} style={{ width: `${animated}%` }} />
          </div>
        </div>
      </div>
      {funnel_drop_points.length > 0 && (
        <div className="mt-4 flex flex-col gap-2">
          <p className="text-xs font-medium text-zinc-500">Tespit edilen huni sorunları:</p>
          {funnel_drop_points.map((point, i) => (
            <div key={i} className="flex items-start gap-2 rounded-lg border border-amber-500/15 bg-amber-500/5 px-3 py-2">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" className="mt-0.5 shrink-0">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <p className="text-xs leading-relaxed text-amber-300/80">{point}</p>
            </div>
          ))}
        </div>
      )}
    </InsightCard>
  );
}

// ── Animated GEO Score ────────────────────────────────────────────────────────

function GeoScoreCard({ score, suggested_title, suggested_description }: {
  score: number; suggested_title: string; suggested_description: string;
}) {
  const animated = useCountUp(score);
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <InsightCard title="GEO Skoru">
        <div className="flex items-end gap-3">
          <p className={`text-5xl font-bold tabular-nums ${score >= 70 ? "text-emerald-400" : score >= 40 ? "text-amber-400" : "text-red-400"}`}>
            {animated}
          </p>
          <div className="pb-1">
            <p className="text-xs text-zinc-500">/100 · GEO skoru</p>
            <p className="text-xs text-zinc-600">{score >= 70 ? "İyi görünürlük" : score >= 40 ? "Orta görünürlük" : "Düşük görünürlük"}</p>
          </div>
        </div>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-zinc-800">
          <div
            className={`h-full rounded-full transition-all duration-1000 ${score >= 70 ? "bg-emerald-500" : score >= 40 ? "bg-amber-500" : "bg-red-500"}`}
            style={{ width: `${animated}%` }}
          />
        </div>
      </InsightCard>

      {suggested_title && (
        <InsightCard
          title="Önerilen Başlık"
          action={<CopyButton text={suggested_title} />}
        >
          <p className="text-sm font-medium leading-relaxed text-zinc-200">{suggested_title}</p>
          {suggested_description && (
            <div className="mt-2 flex items-start justify-between gap-2">
              <p className="text-xs leading-relaxed text-zinc-500">{suggested_description}</p>
              <CopyButton text={suggested_description} />
            </div>
          )}
        </InsightCard>
      )}
    </div>
  );
}

// ── Competitor Insight ────────────────────────────────────────────────────────

function CompetitorCard({ insight }: { insight: string }) {
  const sentences = insight.split(/(?<=[.!?])\s+/).filter(Boolean);
  return (
    <div className="rounded-2xl border border-emerald-500/20 bg-zinc-900/80 p-5">
      <div className="mb-4 flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/15">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
            <circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
          </svg>
        </div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">Rakip İstihbaratı</h2>
        <span className="rounded-full border border-emerald-500/20 bg-emerald-500/8 px-2 py-0.5 text-xs font-medium text-emerald-400">
          Google Search
        </span>
      </div>
      <div className="flex flex-col gap-2">
        {sentences.map((s, i) => (
          <div key={i} className="flex items-start gap-2.5">
            <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500/60" />
            <p className="text-sm leading-relaxed text-zinc-300">{s}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Download helper ───────────────────────────────────────────────────────────

function downloadJson(data: AnalyzeResponse) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `doThis-analiz-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AnalyzePage() {
  const router = useRouter();
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem("doThisResult");
    if (!raw) { router.push("/"); return; }
    try { setResult(JSON.parse(raw) as AnalyzeResponse); }
    catch { router.push("/"); }
  }, [router]);

  if (!result) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950">
        <div className="flex items-center gap-3 text-zinc-500">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-700 border-t-zinc-400" />
          <span className="text-sm">Yükleniyor...</span>
        </div>
      </div>
    );
  }

  const hasAdData = result.ad_waste_pct !== null || result.keyword_roi_map?.length > 0;
  const hasReturnData = result.return_rate !== null;
  const adTypeLabel = result.ad_type ? (AD_TYPE_LABELS[result.ad_type] ?? result.ad_type) : null;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50">

      {/* ── Sticky Header ── */}
      <header className="sticky top-0 z-40 border-b border-zinc-800/60 bg-zinc-950/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-3">
          <Link href="/" className="flex items-center gap-2 text-sm font-medium text-zinc-500 transition-colors hover:text-zinc-300">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
            </svg>
            Yeni Analiz
          </Link>
          <Image src="/Logo.png" alt="doThis" width={72} height={26} className="h-6 w-auto object-contain" />
          <div className="flex items-center gap-2">
            {result.used_fixture && (
              <span className="rounded-full border border-amber-500/20 bg-amber-500/8 px-3 py-1 text-xs font-medium text-amber-400">Demo</span>
            )}
            {adTypeLabel && (
              <span className="rounded-full border border-zinc-700 bg-zinc-800 px-3 py-1 text-xs font-medium text-zinc-400">{adTypeLabel}</span>
            )}
            <button
              type="button"
              onClick={() => downloadJson(result)}
              title="JSON olarak indir"
              className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-400 transition-all hover:border-zinc-700 hover:text-zinc-200"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              İndir
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-10">

        {/* ── Metric Cards ── */}
        <div className="mb-8 grid gap-4 sm:grid-cols-3">
          <MetricCard label="GEO Skoru" value={result.geo_score} colorScale="geo" sublabel="Yapay zeka görünürlüğü" />
          <MetricCard label="İade Oranı" value={result.return_rate} colorScale="return" sublabel="Geri dönen ürün oranı" />
          <MetricCard label="Reklam İsrafı" value={result.ad_waste_pct} colorScale="waste" sublabel="Boşa giden bütçe" />
        </div>

        {/* ── Combined Insight ── */}
        {result.combined_insight && (
          <div className="mb-8">
            <CombinedInsightCard insight={result.combined_insight} actions={result.actions} />
          </div>
        )}

        {/* ── GEO Analysis ── */}
        <div className="mb-8">
          <SectionHeader
            icon={<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" /></svg>}
            title="GEO Görünürlük Analizi"
          />
          <div className="flex flex-col gap-3">
            <GeoScoreCard
              score={result.geo_score}
              suggested_title={result.geo_suggested_title}
              suggested_description={result.geo_suggested_description}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              {result.geo_missing_keywords?.length > 0 && (
                <InsightCard title="Eksik Anahtar Kelimeler">
                  <div className="flex flex-wrap gap-1.5">
                    {result.geo_missing_keywords.map((kw) => <KeywordBadge key={kw} keyword={kw} variant="warning" />)}
                  </div>
                </InsightCard>
              )}
              {result.geo_competitor_keywords?.length > 0 && (
                <InsightCard title="Rakip Anahtar Kelimeleri">
                  <div className="flex flex-wrap gap-1.5">
                    {result.geo_competitor_keywords.map((kw) => <KeywordBadge key={kw} keyword={kw} variant="default" />)}
                  </div>
                </InsightCard>
              )}
            </div>
          </div>
        </div>

        {/* ── Competitor Intelligence ── */}
        {result.competitor_insight && (
          <div className="mb-8">
            <CompetitorCard insight={result.competitor_insight} />
          </div>
        )}

        {/* ── Ad Analysis ── */}
        {hasAdData && (
          <div className="mb-8">
            <SectionHeader
              icon={<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2"><line x1="12" y1="20" x2="12" y2="10" /><line x1="18" y1="20" x2="18" y2="4" /><line x1="6" y1="20" x2="6" y2="16" /></svg>}
              title="Reklam Performans Analizi"
              badge={adTypeLabel ?? undefined}
            />
            <div className="flex flex-col gap-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <FunnelRow result={result} />
                {result.budget_efficiency_score !== null && result.budget_efficiency_score !== undefined && (
                  <BudgetEfficiencyCard score={result.budget_efficiency_score} funnel_drop_points={result.funnel_drop_points ?? []} />
                )}
              </div>
              {result.keyword_roi_map?.length > 0 && <KeywordRoiTable data={result.keyword_roi_map} />}
              {(result.ad_format_insights || result.audience_analysis) && (
                <div className="grid gap-3 sm:grid-cols-2">
                  {result.ad_format_insights && (
                    <InsightCard title={`${adTypeLabel ?? "Reklam"} Formatı Tespitleri`}>
                      <p className="text-sm leading-relaxed text-zinc-300">{result.ad_format_insights}</p>
                    </InsightCard>
                  )}
                  {result.audience_analysis && (
                    <InsightCard title="Kitle Sıcaklığı Analizi">
                      <p className="text-sm leading-relaxed text-zinc-300">{result.audience_analysis}</p>
                    </InsightCard>
                  )}
                </div>
              )}
              {result.high_return_keywords?.length > 0 && (
                <InsightCard title="Yüksek İade Riskli Reklamlar" accent="border-red-500/15">
                  <div className="flex flex-col gap-3">
                    {result.high_return_keywords.slice(0, 5).map((kw, i) => (
                      <div key={i} className="flex flex-col gap-1 rounded-lg border border-zinc-800 bg-zinc-950 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-medium text-zinc-200">{kw.keyword}</span>
                          <div className="flex items-center gap-2">
                            {kw.audience_temperature && kw.audience_temperature !== "bilinmiyor" && (
                              <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-xs text-zinc-500">{kw.audience_temperature}</span>
                            )}
                            <span className="text-xs font-semibold text-red-400">
                              ₺{(kw.spend ?? 0).toLocaleString("tr-TR", { maximumFractionDigits: 0 })} · %{((kw.return_rate ?? 0) * 100).toFixed(0)} iade
                            </span>
                          </div>
                        </div>
                        <p className="text-xs leading-relaxed text-zinc-500">{kw.root_cause}</p>
                      </div>
                    ))}
                  </div>
                </InsightCard>
              )}
            </div>
          </div>
        )}

        {/* ── Return Analysis ── */}
        {hasReturnData && (result.top_return_reason || (result.root_causes?.length > 0)) && (
          <div className="mb-8">
            <SectionHeader
              icon={<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2"><polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 102.13-9.36L1 10" /></svg>}
              title="İade Analizi"
            />
            <div className="grid gap-3 sm:grid-cols-2">
              {result.top_return_reason && (
                <InsightCard title="Birincil İade Sebebi" accent="border-red-500/15">
                  <div className="flex items-start gap-2.5">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2" className="mt-0.5 shrink-0">
                      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                      <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                    <p className="text-sm leading-relaxed text-zinc-300">{result.top_return_reason}</p>
                  </div>
                </InsightCard>
              )}
              {result.root_causes?.length > 0 && (
                <InsightCard title="Kök Sebepler">
                  <ul className="flex flex-col gap-2">
                    {result.root_causes.map((cause, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
                        <p className="text-sm leading-relaxed text-zinc-300">{cause}</p>
                      </li>
                    ))}
                  </ul>
                </InsightCard>
              )}
            </div>
          </div>
        )}

        {/* ── Action Plan ── */}
        <div className="mb-8">
          <SectionHeader
            icon={<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>}
            title="Öncelikli Aksiyon Planı"
            badge={`${result.actions.length} adım`}
          />
          <ActionList actions={result.actions} />
        </div>

        {/* ── Footer ── */}
        <div className="flex items-center justify-between border-t border-zinc-800 pt-6">
          <button
            type="button"
            onClick={() => { localStorage.removeItem("doThisResult"); router.push("/"); }}
            className="flex items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-2.5 text-sm font-medium text-zinc-400 transition-all hover:border-zinc-700 hover:text-zinc-200"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 102.13-9.36L1 10" />
            </svg>
            Yeniden analiz et
          </button>
          <button
            type="button"
            onClick={() => downloadJson(result)}
            className="flex items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-2.5 text-sm font-medium text-zinc-400 transition-all hover:border-zinc-700 hover:text-zinc-200"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Raporu İndir
          </button>
        </div>

      </main>
    </div>
  );
}
