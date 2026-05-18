"use client";

interface UrlInputProps {
  value: string;
  onChange: (value: string) => void;
}

export default function UrlInput({ value, onChange }: UrlInputProps) {
  const isValid = value.trim().startsWith("http");

  return (
    <div className="relative flex items-center">
      <div className="absolute left-4 text-zinc-500">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
          <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
        </svg>
      </div>
      <input
        type="url"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Ürün linkini yapıştır — Trendyol, Hepsiburada, Amazon..."
        className="w-full rounded-xl border border-zinc-800 bg-zinc-900 pl-10 pr-10 py-3.5 text-sm text-zinc-100 placeholder:text-zinc-600 outline-none transition-all focus:border-violet-500 focus:ring-2 focus:ring-violet-500/15"
      />
      {isValid && (
        <div className="absolute right-4 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/15">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="3">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      )}
    </div>
  );
}
