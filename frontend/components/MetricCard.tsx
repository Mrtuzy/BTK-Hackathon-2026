"use client";

type ColorScale = "geo" | "return" | "waste";

interface MetricCardProps {
  label: string;
  value: number | null;
  colorScale: ColorScale;
  sublabel?: string;
}

interface Tone {
  ring: string;
  icon: string;
  value: string;
  bg: string;
  badge: string;
  badgeText: string;
}

function resolveTone(value: number | null, scale: ColorScale): { tone: Tone; display: string; status: string } {
  const good: Tone = {
    ring: "ring-emerald-500/20",
    icon: "text-emerald-500",
    value: "text-emerald-400",
    bg: "bg-emerald-500/8",
    badge: "bg-emerald-500/15",
    badgeText: "text-emerald-400",
  };
  const warn: Tone = {
    ring: "ring-amber-500/20",
    icon: "text-amber-500",
    value: "text-amber-400",
    bg: "bg-amber-500/8",
    badge: "bg-amber-500/15",
    badgeText: "text-amber-400",
  };
  const bad: Tone = {
    ring: "ring-red-500/20",
    icon: "text-red-500",
    value: "text-red-400",
    bg: "bg-red-500/8",
    badge: "bg-red-500/15",
    badgeText: "text-red-400",
  };
  const neutral: Tone = {
    ring: "ring-zinc-700/50",
    icon: "text-zinc-600",
    value: "text-zinc-500",
    bg: "bg-zinc-800/50",
    badge: "bg-zinc-800",
    badgeText: "text-zinc-500",
  };

  if (value === null) {
    return { tone: neutral, display: "—", status: "Veri yok" };
  }

  if (scale === "geo") {
    const tone = value >= 70 ? good : value >= 40 ? warn : bad;
    const status = value >= 70 ? "İyi görünürlük" : value >= 40 ? "Orta görünürlük" : "Düşük görünürlük";
    return { tone, display: Math.round(value).toString(), status };
  }

  const pct = Math.round(value * 100);
  if (scale === "return") {
    const tone = value < 0.1 ? good : value < 0.2 ? warn : bad;
    const status = value < 0.1 ? "Sağlıklı" : value < 0.2 ? "Dikkat" : "Yüksek risk";
    return { tone, display: `${pct}%`, status };
  }

  const tone = value < 0.15 ? good : value < 0.35 ? warn : bad;
  const status = value < 0.15 ? "Verimli" : value < 0.35 ? "İyileştirilebilir" : "Yüksek israf";
  return { tone, display: `${pct}%`, status };
}

const icons: Record<ColorScale, React.ReactNode> = {
  geo: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
    </svg>
  ),
  return: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" /><polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
  waste: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
    </svg>
  ),
};

export default function MetricCard({ label, value, colorScale, sublabel }: MetricCardProps) {
  const { tone, display, status } = resolveTone(value, colorScale);

  return (
    <div className={`relative overflow-hidden rounded-2xl ring-1 ${tone.ring} ${tone.bg} p-5`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">{label}</p>
          {sublabel && <p className="text-xs text-zinc-600">{sublabel}</p>}
        </div>
        <div className={`${tone.icon} opacity-60`}>{icons[colorScale]}</div>
      </div>
      <p className={`mt-3 text-4xl font-bold tabular-nums ${tone.value}`}>{display}</p>
      <div className="mt-3 flex items-center gap-2">
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tone.badge} ${tone.badgeText}`}>
          {status}
        </span>
      </div>
    </div>
  );
}
