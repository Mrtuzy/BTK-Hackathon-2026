"use client";

import { useEffect, useState } from "react";

interface AgentProgressProps {
  isLoading: boolean;
}

const steps = [
  { label: "Ürün sayfası okunuyor", detail: "Playwright ile scraping" },
  { label: "GEO analizi", detail: "Yapay zeka görünürlük skoru hesaplanıyor" },
  { label: "Reklam & iade korelasyonu", detail: "Bütçe israfı tespit ediliyor" },
  { label: "Aksiyon listesi", detail: "Öncelikli öneriler oluşturuluyor" },
];

export default function AgentProgress({ isLoading }: AgentProgressProps) {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (!isLoading) {
      setActiveStep(0);
      return;
    }
    setActiveStep(0);
    const interval = setInterval(() => {
      setActiveStep((cur) => (cur < steps.length - 1 ? cur + 1 : cur));
    }, 4000);
    return () => clearInterval(interval);
  }, [isLoading]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <div className="h-2 w-2 animate-pulse rounded-full bg-violet-500" />
        <p className="text-sm font-medium text-zinc-300">Analiz yapılıyor...</p>
      </div>

      <div className="flex flex-col gap-2">
        {steps.map((step, i) => {
          const isDone = i < activeStep;
          const isActive = i === activeStep;
          const isPending = i > activeStep;

          return (
            <div
              key={step.label}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 transition-all ${
                isActive ? "bg-violet-500/10 border border-violet-500/20" : "border border-transparent"
              }`}
            >
              <div className="flex h-6 w-6 shrink-0 items-center justify-center">
                {isDone && (
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </div>
                )}
                {isActive && (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
                )}
                {isPending && (
                  <div className="h-2 w-2 rounded-full bg-zinc-700" />
                )}
              </div>
              <div>
                <p className={`text-sm font-medium ${isActive ? "text-zinc-100" : isDone ? "text-zinc-400" : "text-zinc-600"}`}>
                  {step.label}
                </p>
                {isActive && (
                  <p className="text-xs text-zinc-500">{step.detail}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="h-1 w-full overflow-hidden rounded-full bg-zinc-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 transition-all duration-700"
          style={{ width: `${((activeStep + 1) / steps.length) * 100}%` }}
        />
      </div>
    </div>
  );
}
