export type ActionPriority = "critical" | "important" | "improvement";

export interface ActionItem {
  priority: ActionPriority;
  title: string;
  description: string;
  estimated_impact: string;
  how_to_apply: string;
}

export interface KeywordRoiEntry {
  keyword: string;
  spend: number;
  clicks: number;
  impressions: number;
  conversions: number;
  return_quantity: number;
  return_rate: number;
  ctr: number;
  conversion_rate: number;
  cpa: number | null;
  efficiency_score: number;
}

export interface HighReturnKeyword {
  keyword: string;
  return_rate: number;
  spend: number;
  root_cause: string;
  audience_temperature?: string;
}

export interface AnalyzeRequest {
  url: string;
  adCsv?: File | null;
  returnsCsv?: File | null;
}

export interface AnalyzeResponse {
  geo_score: number;
  return_rate: number | null;
  ad_waste_pct: number | null;
  actions: ActionItem[];
  used_fixture: boolean;
  geo_suggested_title: string;
  geo_suggested_description: string;
  geo_missing_keywords: string[];
  geo_competitor_keywords: string[];
  ad_format_insights: string | null;
  audience_analysis: string | null;
  ad_type: string | null;
  top_return_reason: string | null;
  keyword_roi_map: KeywordRoiEntry[];
  budget_efficiency_score: number | null;
  funnel_drop_points: string[];
  cost_per_conversion_avg: number | null;
  combined_insight: string | null;
  competitor_insight: string | null;
  high_return_keywords: HighReturnKeyword[];
  root_causes: string[];
  total_impressions: number;
  total_clicks: number;
  total_conversions: number;
  total_returns: number;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.trim() || "http://localhost:8000";

export async function analyze(
  request: AnalyzeRequest,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append("url", request.url);

  if (request.adCsv) {
    formData.append("ad_csv", request.adCsv);
  }

  if (request.returnsCsv) {
    formData.append("returns_csv", request.returnsCsv);
  }

  const response = await fetch(`${API_URL}/api/analyze`, {
    method: "POST",
    body: formData,
    signal,
  });

  if (!response.ok) {
    const raw = await response.text();
    let message = raw;

    try {
      const parsed = JSON.parse(raw) as { detail?: string };
      if (parsed.detail) {
        message = parsed.detail;
      }
    } catch {
      // Non-JSON error bodies are fine.
    }

    throw new ApiError(
      response.status,
      message || `Request failed: ${response.status}`,
    );
  }

  return (await response.json()) as AnalyzeResponse;
}
