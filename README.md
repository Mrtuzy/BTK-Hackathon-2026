# doThis

E-ticaret satıcıları için kâr kaçağı dedektörü.

Bir ürün URL'si + isteğe bağlı reklam/iade CSV dosyaları yapıştır. doThis şunları analiz eder:
- **GEO Skoru** — Ürünün AI arama motorlarında (ChatGPT, Gemini, Perplexity) neden görünmez olduğu
- **Reklam × İade Korelasyonu** — Hangi reklam anahtar kelimelerinin bütçeyi yaktığı
- **Öncelikli Aksiyon Listesi** — Somut, etki puanlı yapılacaklar listesi

---

## Tech Stack

| Katman | Teknoloji |
|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| Backend | Python 3.11 + FastAPI |
| AI Orkestrasyon | LangGraph + LangChain |
| AI Modeli | Gemini 2.5 Flash |
| Web Scraping | Playwright (async) |
| Scraping Fallback | JSON fixtures (internet olmadan da çalışır) |
| Veritabanı | Yok — tamamen stateless |

---

## Gereksinimler

- **Python 3.11+** (3.12 de çalışır; 3.10 ve altı desteklenmez)
- **Node.js 18+** (20 LTS önerilir)
- **Gemini API Anahtarı** — [aistudio.google.com](https://aistudio.google.com) adresinden ücretsiz alınabilir

---

## Kurulum

### 1. Repoyu klonla

```bash
git clone https://github.com/Mertguden/doThis.git
cd doThis
```

### 2. Backend kurulumu

```bash
cd backend
```

**Sanal ortam oluştur ve aktifleştir:**

Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Bağımlılıkları yükle:**
```bash
pip install -r requirements.txt
```

**Playwright tarayıcısını yükle** _(bu adım zorunlu — atlanırsa scraping çalışmaz):_
```bash
python -m playwright install chromium
```

**Ortam değişkenlerini ayarla:**

Windows:
```bash
copy .env.example .env
```

macOS / Linux:
```bash
cp .env.example .env
```

Ardından `backend/.env` dosyasını aç ve `GEMINI_API_KEY` değerini gir:
```
GEMINI_API_KEY=your_key_here
PLAYWRIGHT_HEADLESS=true
```

**Backend'i başlat:**
```bash
uvicorn main:app --reload
```

Backend `http://localhost:8000` adresinde çalışır.
Sağlık kontrolü: [http://localhost:8000/health](http://localhost:8000/health)

---

### 3. Frontend kurulumu

Yeni bir terminal açıp devam et:

```bash
cd frontend
npm install
```

**`frontend/.env.local` dosyasını oluştur:**

Windows:
```bash
copy .env.local.example .env.local
```

macOS / Linux:
```bash
cp .env.local.example .env.local
```

Ya da manuel oluştur — dosya içeriği:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Frontend'i başlat:**
```bash
npm run dev
```

Uygulama `http://localhost:3000` adresinde açılır.

---

## API

```
POST /api/analyze
Content-Type: multipart/form-data

  url          string  (zorunlu)       — ürün sayfası URL'si
  ad_csv       file    (isteğe bağlı)  — reklam verisi CSV
  returns_csv  file    (isteğe bağlı)  — iade verisi CSV

GET /health → {"status": "ok", "version": "1.0.0"}
```

### Desteklenen CSV formatları

| Parametre | Desteklenen formatlar |
|---|---|
| `ad_csv` | Google Ads, Meta Ads, Trendyol Reklam Raporu |
| `returns_csv` | Trendyol İade Raporu |

---

## Proje Yapısı

```
backend/
├── main.py                           # FastAPI başlangıç noktası, DI wiring
├── config.py                         # Ortam değişkenleri
├── domain/
│   ├── entities.py                   # Saf dataclass'lar (ProductData, GeoReport vb.)
│   ├── ports.py                      # Abstract interface'ler
│   └── services/                     # İş mantığı (GEO, Korelasyon, Aksiyon)
├── application/
│   ├── analysis_pipeline.py          # LangGraph orkestrasyonu
│   └── dto.py                        # API request/response şekilleri
├── adapters/
│   ├── inbound/analyze_controller.py
│   └── outbound/
│       ├── gemini_language_model.py
│       ├── playwright_scraper.py
│       └── csv_parser_factory.py
└── infrastructure/
    └── scraping/fixtures/            # Scraping başarısız olursa kullanılan örnek veriler

frontend/
├── app/
│   ├── page.tsx                      # Giriş sayfası
│   └── analyze/page.tsx              # Sonuçlar sayfası
├── components/                       # UI bileşenleri
└── lib/api.ts                        # API istemcisi
```

---

## Sorun Giderme

**`ModuleNotFoundError: No module named 'playwright'`**
→ Sanal ortamın aktif olduğundan emin ol: `.venv\Scripts\activate` (Windows) veya `source .venv/bin/activate` (macOS/Linux)

**`playwright._impl._errors.Error: Executable doesn't exist`**
→ `python -m playwright install chromium` komutunu çalıştırmayı unutmuşsun.

**Scraping her zaman demo/fixture modu döndürüyor**
→ Playwright kurulumu eksik ya da URL geçersiz olabilir. `uvicorn` loglarında `Scrape failed` satırını kontrol et.

**`GEMINI_API_KEY` hatası**
→ `backend/.env` dosyasını oluştur ve geçerli API anahtarını gir. [aistudio.google.com](https://aistudio.google.com) adresinden ücretsiz alabilirsin.

**Port zaten kullanımda**
→ Backend için `uvicorn main:app --reload --port 8001`, frontend için `npm run dev -- --port 3001`. `frontend/.env.local` içindeki `NEXT_PUBLIC_API_URL`'i de güncellemeyi unutma.

---

## Notlar

- Playwright scraping başarısız olursa otomatik olarak `infrastructure/scraping/fixtures/` içindeki örnek veriye döner — internet bağlantısı olmadan da demo yapılabilir.
- Tüm analiz session-scoped'tur; hiçbir veri saklanmaz.
- Gemini rate limit aşılırsa sistem otomatik olarak bekleyip tekrar dener.
