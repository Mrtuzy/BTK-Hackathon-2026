"use client";

import { useMemo, useState } from "react";

interface CsvUploadProps {
  onAdCsv: (file: File | null) => void;
  onReturnsCsv: (file: File | null) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface UploadZoneProps {
  id: string;
  label: string;
  icon: React.ReactNode;
  hint: string;
  file: File | null;
  error: string | null;
  onFile: (file: File | null) => void;
}

function UploadZone({ id, label, icon, hint, file, error, onFile }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);

  const handleFile = (f: File | null) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) {
      onFile(null);
      return;
    }
    onFile(f);
  };

  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={id}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFile(e.dataTransfer.files[0] ?? null);
        }}
        className={`flex cursor-pointer flex-col gap-3 rounded-xl border border-dashed px-4 py-5 transition-all ${
          file
            ? "border-violet-500/50 bg-violet-500/5"
            : dragging
            ? "border-violet-500 bg-violet-500/10"
            : "border-zinc-700 bg-zinc-900 hover:border-zinc-600 hover:bg-zinc-800/50"
        }`}
      >
        <div className="flex items-center gap-3">
          <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${file ? "bg-violet-500/20 text-violet-400" : "bg-zinc-800 text-zinc-500"}`}>
            {file ? (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : icon}
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-zinc-200">{label}</span>
            <span className="text-xs text-zinc-500">{hint}</span>
          </div>
        </div>

        {file ? (
          <div className="flex items-center gap-2">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span className="text-xs text-violet-400">{file.name}</span>
            <span className="text-xs text-zinc-600">• {formatFileSize(file.size)}</span>
          </div>
        ) : (
          <span className="text-xs text-zinc-600">.csv sürükle veya tıkla</span>
        )}

        <input
          id={id}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />
      </label>

      {file && (
        <button
          type="button"
          onClick={() => onFile(null)}
          className="self-start text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
        >
          × Kaldır
        </button>
      )}
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}

export default function CsvUpload({ onAdCsv, onReturnsCsv }: CsvUploadProps) {
  const [adFile, setAdFile] = useState<File | null>(null);
  const [returnsFile, setReturnsFile] = useState<File | null>(null);

  const adIcon = (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <path d="M8 21h8M12 17v4" />
    </svg>
  );

  const returnsIcon = (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
    </svg>
  );

  const handleAdFile = (file: File | null) => {
    setAdFile(file);
    onAdCsv(file);
  };

  const handleReturnsFile = (file: File | null) => {
    setReturnsFile(file);
    onReturnsCsv(file);
  };

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <UploadZone
        id="ad-csv"
        label="Reklam Verisi"
        icon={adIcon}
        hint="Google Ads · Meta Ads · Trendyol"
        file={adFile}
        error={null}
        onFile={handleAdFile}
      />
      <UploadZone
        id="returns-csv"
        label="İade Raporu"
        icon={returnsIcon}
        hint="Trendyol iade raporu CSV"
        file={returnsFile}
        error={null}
        onFile={handleReturnsFile}
      />
    </div>
  );
}
