"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import AgentProgress from "@/components/AgentProgress";
import CsvUpload from "@/components/CsvUpload";
import UrlInput from "@/components/UrlInput";
import { ApiError, analyze, type AnalyzeResponse } from "@/lib/api";

interface HistoryEntry {
  id: string;
  timestamp: number;
  url: string;
  geo_score: number;
  result: AnalyzeResponse;
}

function loadHistory(): HistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem("doThisHistory") ?? "[]") as HistoryEntry[];
  } catch {
    return [];
  }
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="text-sm text-zinc-400 transition-colors hover:text-zinc-100"
      onClick={(e) => {
        e.preventDefault();
        document.querySelector(href)?.scrollIntoView({ behavior: "smooth" });
      }}
    >
      {children}
    </a>
  );
}

function FeatureCard({ icon, title, description, accent }: {
  icon: React.ReactNode; title: string; description: string; accent: string;
}) {
  return (
    <div className="group flex flex-col gap-4 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6 transition-all hover:border-zinc-700 hover:bg-zinc-900">
      <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${accent}`}>{icon}</div>
      <div>
        <h3 className="mb-2 text-base font-semibold text-zinc-100">{title}</h3>
        <p className="text-sm leading-relaxed text-zinc-500">{description}</p>
      </div>
    </div>
  );
}

function Step({ number, title, description, last }: {
  number: string; title: string; description: string; last?: boolean;
}) {
  return (
    <div className="flex gap-5">
      <div className="flex flex-col items-center">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-violet-500/30 bg-violet-500/10 text-sm font-bold text-violet-400">
          {number}
        </div>
        {!last && <div className="mt-2 w-px flex-1 bg-gradient-to-b from-violet-500/20 to-transparent" />}
      </div>
      <div className="pb-10">
        <p className="mb-1 text-base font-semibold text-zinc-100">{title}</p>
        <p className="text-sm leading-relaxed text-zinc-500">{description}</p>
      </div>
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const abortRef = useRef<AbortController | null>(null);
  const [url, setUrl] = useState("");
  const [adCsv, setAdCsv] = useState<File | null>(null);
  const [returnsCsv, setReturnsCsv] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  const runAnalysis = async (opts: { url: string; adCsv: File | null; returnsCsv: File | null }) => {
    setErrorMessage(null);
    setIsLoading(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const data = await analyze(
        { url: opts.url, adCsv: opts.adCsv, returnsCsv: opts.returnsCsv },
        controller.signal,
      );
      localStorage.setItem("doThisResult", JSON.stringify(data));

      // Save to history
      const entry: HistoryEntry = {
        id: Date.now().toString(),
        timestamp: Date.now(),
        url: opts.url,
        geo_score: data.geo_score,
        result: data,
      };
      const prev = loadHistory();
      const next = [entry, ...prev].slice(0, 5);
      localStorage.setItem("doThisHistory", JSON.stringify(next));

      router.push("/analyze");
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(
          error.status === 400
            ? "CSV formatı tanınamadı. Google Ads, Meta Ads veya Trendyol formatını deneyin."
            : error.status === 500
            ? "Analiz sırasında bir hata oluştu. Lütfen tekrar deneyin."
            : error.message,
        );
      } else if (error instanceof Error && error.name === "AbortError") {
        setErrorMessage(null);
      } else {
        setErrorMessage("Bağlantı hatası. İnternet bağlantınızı kontrol edin.");
      }
    } finally {
      setIsLoading(false);
      abortRef.current = null;
    }
  };

  const handleAnalyze = () => {
    if (!url.trim() || isLoading) return;
    void runAnalysis({ url: url.trim(), adCsv, returnsCsv });
  };

  const handleDemo = async () => {
    if (isLoading) return;
    const toFile = async (path: string, name: string) => {
      const res = await fetch(path);
      const blob = await res.blob();
      return new File([blob], name, { type: "text/csv" });
    };
    const [adCsvDemo, returnsCsvDemo] = await Promise.all([
      toFile("/demo/ads.csv", "demo_ads.csv"),
      toFile("/demo/returns.csv", "demo_returns.csv"),
    ]);
    void runAnalysis({
      url: "https://www.trendyol.com/demo-product",
      adCsv: adCsvDemo,
      returnsCsv: returnsCsvDemo,
    });
  };

  const loadHistoryEntry = (entry: HistoryEntry) => {
    localStorage.setItem("doThisResult", JSON.stringify(entry.result));
    router.push("/analyze");
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50">

      {/* ── Navigation ── */}
      <nav className="fixed top-0 z-50 w-full border-b border-zinc-800/60 bg-zinc-950/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2.5">
            <Image src="/Logo.png" alt="doThis" width={90} height={32} className="h-8 w-auto object-contain" priority />
          </div>
          <div className="flex items-center gap-6">
            <div className="hidden items-center gap-6 sm:flex">
              <NavLink href="#nasil-calisir">Nasıl Çalışır</NavLink>
              <NavLink href="#ozellikler">Özellikler</NavLink>
              <NavLink href="#hakkimizda">Hakkımızda</NavLink>
            </div>
            <button
              type="button"
              onClick={() => document.querySelector("#analiz")?.scrollIntoView({ behavior: "smooth" })}
              className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500"
            >
              Analizi Başlat
            </button>
          </div>
        </div>
      </nav>

      {/* ── Hero + Form ── */}
      <section id="analiz" className="relative overflow-hidden pt-24">
        <div className="pointer-events-none absolute inset-0">
          <div className="grid-bg absolute inset-0" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_0%,rgba(139,92,246,0.12),transparent)]" />
        </div>

        <div className="relative z-10 mx-auto max-w-3xl px-6 pb-16 pt-16 text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-violet-500/20 bg-violet-500/8 px-4 py-1.5">
            <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400" />
            <span className="text-xs font-medium text-violet-300">AI destekli kâr analizi · Ücretsiz · Saniyeler içinde</span>
          </div>

          <h1 className="font-display text-5xl font-semibold leading-[1.1] tracking-tight text-zinc-50 sm:text-6xl">
            Kârını hangi sorun
            <br />
            <span className="bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
              yiyor?
            </span>{" "}
            15 sn&apos;de öğren.
          </h1>

          <p className="mx-auto mt-5 max-w-lg text-base leading-relaxed text-zinc-400">
            GEO görünürlüğü, reklam israfı ve iade korelasyonunu birleştiren
            tek analiz platformu. Rakiplerinizden önce görün, önce kazan.
          </p>

          {/* Form card */}
          <div className="mt-10 rounded-2xl border border-zinc-800 bg-zinc-900/80 p-6 shadow-2xl shadow-black/50 backdrop-blur-sm">
            <div className="flex flex-col gap-4">
              <UrlInput value={url} onChange={setUrl} />

              {errorMessage && (
                <div className="flex items-start gap-2.5 rounded-lg border border-red-500/20 bg-red-500/8 px-3.5 py-3">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2" className="mt-0.5 shrink-0">
                    <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <p className="text-xs leading-relaxed text-red-400">{errorMessage}</p>
                </div>
              )}

              <CsvUpload onAdCsv={setAdCsv} onReturnsCsv={setReturnsCsv} />

              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={!url.trim() || isLoading}
                  onClick={handleAnalyze}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-3.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {isLoading ? (
                    <>
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Analiz ediliyor...
                    </>
                  ) : (
                    <>
                      Kâr Analizi Yap
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
                      </svg>
                    </>
                  )}
                </button>
                <button
                  type="button"
                  disabled={isLoading}
                  onClick={handleDemo}
                  title="Örnek ürünle demo analizi çalıştır"
                  className="flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-3.5 text-sm font-medium text-zinc-300 transition-all hover:border-zinc-600 hover:bg-zinc-700 hover:text-zinc-100 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                  Demo
                </button>
              </div>
            </div>

            <div className="mt-5 flex items-center gap-3">
              <div className="h-px flex-1 bg-zinc-800" />
              <span className="text-xs text-zinc-600">desteklenen platformlar</span>
              <div className="h-px flex-1 bg-zinc-800" />
            </div>
            <div className="mt-3 flex flex-wrap justify-center gap-2">
              {["Trendyol", "Hepsiburada", "Amazon TR"].map((p) => (
                <span key={p} className="rounded-md bg-zinc-800 px-2.5 py-1 text-xs text-zinc-500">{p}</span>
              ))}
            </div>
          </div>

          {/* History */}
          {history.length > 0 && (
            <div className="mt-6 text-left">
              <p className="mb-2 text-xs font-medium uppercase tracking-widest text-zinc-600">Son analizler</p>
              <div className="flex flex-col gap-1.5">
                {history.map((entry) => (
                  <button
                    key={entry.id}
                    type="button"
                    onClick={() => loadHistoryEntry(entry)}
                    className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900/60 px-4 py-2.5 text-left transition-all hover:border-zinc-700 hover:bg-zinc-900"
                  >
                    <span className={`text-sm font-bold tabular-nums ${entry.geo_score >= 70 ? "text-emerald-400" : entry.geo_score >= 40 ? "text-amber-400" : "text-red-400"}`}>
                      {entry.geo_score}
                    </span>
                    <span className="flex-1 truncate text-xs text-zinc-400">{entry.url}</span>
                    <span className="shrink-0 text-xs text-zinc-700">
                      {new Date(entry.timestamp).toLocaleDateString("tr-TR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ── Stat Bar ── */}
      <section className="border-y border-zinc-800/60 bg-zinc-900/30">
        <div className="mx-auto max-w-5xl px-6 py-8">
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            {[
              { label: "GEO Görünürlüğü", sub: "ChatGPT & Gemini'de sıralama skoru", icon: "🔍" },
              { label: "Reklam ROI Haritası", sub: "Kelime bazında bütçe verimliliği", icon: "📊" },
              { label: "İade Korelasyonu", sub: "Reklam → iade kök sebep analizi", icon: "↩" },
              { label: "Rakip İstihbaratı", sub: "Gerçek zamanlı rakip karşılaştırma", icon: "⚡" },
            ].map((s) => (
              <div key={s.label} className="flex flex-col gap-1 text-center">
                <span className="text-2xl">{s.icon}</span>
                <span className="text-sm font-semibold text-zinc-200">{s.label}</span>
                <span className="text-xs text-zinc-600">{s.sub}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="nasil-calisir" className="mx-auto max-w-5xl px-6 py-24">
        <div className="mb-14 text-center">
          <p className="mb-3 text-xs font-medium uppercase tracking-widest text-violet-400">Nasıl Çalışır</p>
          <h2 className="font-display text-3xl font-semibold text-zinc-100">3 adımda tam kâr haritası</h2>
          <p className="mx-auto mt-3 max-w-md text-sm text-zinc-500">
            Kurulum yok, kayıt yok. Sadece URL yapıştır — gerisini biz hallederiz.
          </p>
        </div>

        <div className="mx-auto max-w-lg">
          <Step
            number="1"
            title="Ürün URL'sini yapıştır"
            description="Trendyol, Hepsiburada veya Amazon TR'den herhangi bir ürün sayfası linki yeterli. Sistem ürün verilerini, rakip başlıklarını ve fiyat bilgisini otomatik çeker."
          />
          <Step
            number="2"
            title="Reklam ve iade verilerini yükle"
            description="Google Ads, Meta Ads veya Trendyol reklam CSV'nizi sürükle-bırak ile yükle. İade raporunu da ekle. Daha fazla veri, daha derin analiz."
          />
          <Step
            number="3"
            title="Kâr kurtarma planını al"
            description="AI; GEO skoru, reklam israfı, iade korelasyonu ve rakip analizini birleştirerek kopyalanıp uygulanabilir, önceliklendirilmiş bir aksiyon listesi çıkarır."
            last
          />
        </div>
      </section>

      {/* ── Features ── */}
      <section id="ozellikler" className="bg-zinc-900/20">
        <div className="mx-auto max-w-5xl px-6 py-24">
          <div className="mb-14 text-center">
            <p className="mb-3 text-xs font-medium uppercase tracking-widest text-violet-400">Ne Analiz Ediyoruz?</p>
            <h2 className="font-display text-3xl font-semibold text-zinc-100">Dört boyutlu kâr haritası</h2>
            <p className="mx-auto mt-3 max-w-md text-sm text-zinc-500">
              Her analiz tek başına değerlidir. Birlikte, rakiplerin göremediği bağlantıları ortaya çıkarır.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <FeatureCard
              accent="bg-violet-500/15 text-violet-400"
              icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" /></svg>}
              title="GEO Görünürlük"
              description="ChatGPT, Gemini ve Perplexity'de neden görünmüyorsunuz. 4 kriter, 0–100 puan. Eksik kelimeler ve rakip gap analizi."
            />
            <FeatureCard
              accent="bg-cyan-500/15 text-cyan-400"
              icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="20" x2="12" y2="10" /><line x1="18" y1="20" x2="18" y2="4" /><line x1="6" y1="20" x2="6" y2="16" /></svg>}
              title="Reklam ROI Haritası"
              description="Her anahtar kelimenin verimliliği, CTR kalitesi, dönüşüm hunisindeki kayıp noktaları ve CPA analizi."
            />
            <FeatureCard
              accent="bg-amber-500/15 text-amber-400"
              icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 102.13-9.36L1 10" /></svg>}
              title="İade Korelasyonu"
              description="Hangi reklamlar iade getiriyor ve neden. Beklenti-gerçeklik uyumsuzluğu, kitle sıcaklığı ve kök sebep tespiti."
            />
            <FeatureCard
              accent="bg-emerald-500/15 text-emerald-400"
              icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" /></svg>}
              title="Rakip İstihbaratı"
              description="Google Search üzerinden gerçek zamanlı rakip taraması. Lider rakipler ne yapıyor, hangi kelimeleri kullanıyor?"
            />
          </div>
        </div>
      </section>

      {/* ── About ── */}
      <section id="hakkimizda" className="mx-auto max-w-5xl px-6 py-24">
        <div className="grid gap-12 sm:grid-cols-2 sm:items-center">
          <div>
            <p className="mb-3 text-xs font-medium uppercase tracking-widest text-violet-400">Hakkımızda</p>
            <h2 className="font-display text-3xl font-semibold leading-snug text-zinc-100">
              Satıcıların elindeki veriyi,
              <br />
              stratejistler gibi yorumla.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-zinc-500">
              doThis, Türkiye e-ticaret pazarındaki satıcıların kâr sızıntısı noktalarını
              tespit etmek için geliştirilen yapay zeka destekli analiz platformudur.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-zinc-500">
              GEO optimizasyonu, reklam ROI analizi, iade korelasyonu ve rakip
              istihbaratını tek çatı altında birleştirerek hiçbir araçla elde
              edilemeyen içgörüler sunar.
            </p>
          </div>

          <div className="flex flex-col gap-4">
            {[
              { label: "Gerçek zamanlı rakip taraması", desc: "Google Search grounding ile rakiplerin stratejileri anında analiz edilir." },
              { label: "Seçilebilir Gemini modelleri", desc: "Hız ve derinlik arasında seçim yapın: Flash, Pro veya kararlı sürüm." },
              { label: "Stateless & gizlilik öncelikli", desc: "Verileriniz hiçbir yerde saklanmaz. Her analiz sıfırdan başlar, iz bırakmaz." },
            ].map((v) => (
              <div key={v.label} className="flex gap-4 rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
                <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/15">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-200">{v.label}</p>
                  <p className="text-xs text-zinc-500">{v.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className="border-y border-zinc-800/60 bg-zinc-900/30">
        <div className="mx-auto max-w-3xl px-6 py-16 text-center">
          <h2 className="font-display text-3xl font-semibold text-zinc-100">
            Kâr sızıntısı her gün büyüyor.
          </h2>
          <p className="mx-auto mt-3 max-w-md text-sm text-zinc-500">
            Üye olmadan, kart vermeden, kurulum yapmadan. Sadece ürün URL'si.
          </p>
          <button
            type="button"
            onClick={() => document.querySelector("#analiz")?.scrollIntoView({ behavior: "smooth" })}
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-violet-600 px-6 py-3 text-sm font-semibold text-white transition-all hover:bg-violet-500"
          >
            Şimdi Analiz Et
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
            </svg>
          </button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-zinc-800/60">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 px-6 py-8 sm:flex-row">
          <Image src="/Logo.png" alt="doThis" width={72} height={26} className="h-6 w-auto object-contain opacity-70" />
          <div className="flex items-center gap-6">
            <NavLink href="#nasil-calisir">Nasıl Çalışır</NavLink>
            <NavLink href="#hakkimizda">Hakkımızda</NavLink>
            <NavLink href="#analiz">Analiz Yap</NavLink>
          </div>
          <p className="text-xs text-zinc-700">© 2025 doThis</p>
        </div>
      </footer>

      {/* ── Loading overlay ── */}
      {isLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/80 p-6 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl border border-zinc-800 bg-zinc-900 p-6 shadow-2xl">
            <AgentProgress isLoading={isLoading} />
            <button
              type="button"
              onClick={() => { abortRef.current?.abort(); setIsLoading(false); }}
              className="mt-5 w-full rounded-lg border border-zinc-800 py-2 text-xs font-medium text-zinc-500 transition-colors hover:border-zinc-700 hover:text-zinc-400"
            >
              İptal et
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
