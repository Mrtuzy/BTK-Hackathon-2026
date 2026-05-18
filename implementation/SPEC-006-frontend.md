# SPEC-006 — Frontend

Read CLAUDE.md first. TypeScript strict mode, no `any`, Tailwind only.

## Components

### `UrlInput.tsx`
```typescript
interface UrlInputProps {
  value: string;
  onChange: (value: string) => void;
}
```
- Full-width input, 18px text, placeholder: `"Ürün linkini yapıştır (Trendyol, Hepsiburada, Amazon...)"`
- Shows green ✓ icon when value starts with `https://`

### `CsvUpload.tsx`
```typescript
interface CsvUploadProps {
  onAdCsv: (file: File | null) => void;
  onReturnsCsv: (file: File | null) => void;
}
```
- Two side-by-side dashed-border zones: "Reklam raporu" + "İade raporu", both marked "(isteğe bağlı)"
- Accept `.csv` only — show inline error "Sadece .csv dosyası yükleyebilirsiniz" for other types
- When uploaded: show filename + size + "×" remove button
- On remove: call `onXxx(null)`, reset zone to empty state

### `AgentProgress.tsx`
```typescript
interface AgentProgressProps {
  isLoading: boolean;
}
```
- 4 horizontal steps: "Ürün sayfası okunuyor" / "GEO analizi yapılıyor" / "Reklam verisi analiz ediliyor" / "Aksiyon listesi hazırlanıyor"
- Active: spinner icon. Done: ✓. Pending: dot.
- Frontend simulation: advance one step every 3s while `isLoading=true`
- Reset to step 0 when `isLoading` goes false

### `MetricCard.tsx`
```typescript
type ColorScale = "geo" | "return" | "waste";

interface MetricCardProps {
  label: string;
  value: number | null;
  colorScale: ColorScale;
}
```
Color logic:
- `geo`: <40 → red, 40–70 → amber, >70 → green. Display as integer.
- `return`: <0.15 → green, 0.15–0.25 → amber, >0.25 → red. Display as `"31%"`.
- `waste`: <0.20 → green, 0.20–0.40 → amber, >0.40 → red. Display as `"47%"`.
- `null` → value="—", status="Veri yok", color=gray

### `ActionItem.tsx`
```typescript
interface ActionItemProps {
  action: ActionItem;  // from lib/api.ts
}
```
- Left border color: critical=red-500, important=amber-500, improvement=green-500
- Priority badge (small, colored pill) + title
- Description paragraph
- `⚡ {estimatedImpact}` in muted text
- "Nasıl uygulanır? ▼" — click toggles `howToApply` section open/closed
- Top-right copy button: copies `action.title + "\n\n" + action.howToApply` to clipboard, shows "Kopyalandı ✓" toast for 2s

### `ActionList.tsx`
```typescript
interface ActionListProps {
  actions: ActionItem[];
}
```
- Section headers: "🔴 Hemen Yap" (critical), "🟡 Bu Hafta Yap" (important), "🟢 İyileştir" (improvement)
- Only render sections that have items
- Renders `ActionItem` for each action in section

---

## Pages

### `app/page.tsx` — Input Screen
- Top-left: "doThis" wordmark (text, bold, 20px)
- Centered layout, `max-w-xl mx-auto`
- Heading: "Paranızın nerede gittiğini bulun." (bold, 24px)
- Subheading: "Ürün linkini yapıştırın. 15 saniyede kâr sızıntısı haritanız hazır." (muted, 16px)
- `UrlInput` → `CsvUpload` (below) → "Analiz Et" button
- Button: disabled when URL empty or `isLoading=true`
- On click:
  1. Set `isLoading = true`
  2. Call `analyze({url, adCsv, returnsCsv})` from `lib/api.ts`
  3. On success: `localStorage.setItem("doThisResult", JSON.stringify(data))`, `router.push("/analyze")`
  4. On error: set error state, `isLoading = false`
- Show `AgentProgress` in full-screen overlay when `isLoading=true`
- Overlay includes "İptal" button → `AbortController.abort()`, `isLoading = false`

Error display (inline, below URL input):
- 400: "CSV formatı tanınamadı. Google Ads, Meta Ads veya Trendyol formatını deneyin."
- 500: "Analiz sırasında bir hata oluştu. Lütfen tekrar deneyin."
- Network: "Bağlantı hatası. İnternet bağlantınızı kontrol edin."

### `app/analyze/page.tsx` — Results Screen
- On mount: `JSON.parse(localStorage.getItem("doThisResult"))` → if null, redirect to `/`
- Top row: "← Yeni analiz" link (left) + amber "Demo modu" badge if `used_fixture=true` (right)
- 3 `MetricCard`s in a row: GEO Skoru / İade Oranı / Reklam İsrafı
- `ActionList` below
- Bottom: "Yeniden analiz et" button → `localStorage.removeItem("doThisResult")`, `router.push("/")`

---

## Done when

- `npm run build` → zero TypeScript errors
- Input screen: URL empty → button disabled; valid `https://` URL → button enabled + ✓ icon
- `.xlsx` file upload → inline error message shown
- Click "Analiz Et" → loading overlay with 4-step animation appears
- Results screen renders all 3 MetricCards with correct color coding
- `null` metric → shows "—" and "Veri yok"
- `used_fixture=true` → amber "Demo modu" badge visible
- Copy button → clipboard updated + "Kopyalandı ✓" toast
- "Nasıl uygulanır?" expands and collapses on click
