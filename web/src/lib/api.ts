import type { AnalysisRun, BootstrapData, HistoricalMetrics, HistoryItem, ParsedPromotion, PlatformConfig, Product, ProductInput, ProfitAnalysisRequest, ResearchReport } from "@/types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "服务暂时不可用" }));
    throw new Error(body.detail ?? `请求失败 (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>("/health"),
  bootstrap: () => request<BootstrapData>("/ui/bootstrap"),
  history: () => request<HistoryItem[]>("/analysis"),
  products: () => request<Product[]>("/products"),
  product: (id: number) => request<Product>(`/products/${id}`),
  createProduct: (payload: ProductInput) => request<Product>("/products", { method: "POST", body: JSON.stringify(payload) }),
  updateProduct: (id: number, payload: ProductInput) => request<Product>(`/products/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteProduct: (id: number) => request<void>(`/products/${id}`, { method: "DELETE" }),
  savePlatformConfig: (id: number, payload: PlatformConfig) => request<PlatformConfig>(`/products/${id}/platform-configs`, { method: "POST", body: JSON.stringify(payload) }),
  activities: () => request<Array<{ id: number; product_id: number; platform: string; activity_name: string; estimated_sales: number }>>("/activities"),
  activity: (id: number) => request<Record<string, unknown>>(`/activities/${id}`),
  parsePromotion: (url: string, rawText: string, platformHint = "") => {
    const params = new URLSearchParams({ raw_text: rawText });
    if (url) params.set("url", url);
    if (platformHint) params.set("platform_hint", platformHint);
    return request<ParsedPromotion>(`/activities/parse?${params.toString()}`, { method: "POST" });
  },
  createActivity: (productId: number, payload: ProfitAnalysisRequest["activity"]) =>
    request<{ id: number; product_id: number }>(`/activities?product_id=${productId}`, { method: "POST", body: JSON.stringify(payload) }),
  profit: (payload: ProfitAnalysisRequest) => request<AnalysisRun["result"]>("/analysis/profit", { method: "POST", body: JSON.stringify(payload) }),
  research: (analysis: ProfitAnalysisRequest, historical: HistoricalMetrics, evidence_urls: string[]) => request<ResearchReport>("/analysis/research", { method: "POST", body: JSON.stringify({ analysis, historical, evidence_urls }) }),
  compare: (payloads: ProfitAnalysisRequest[]) => request<AnalysisRun["result"][]>("/analysis/compare", { method: "POST", body: JSON.stringify(payloads) }),
  runAnalysis: (payload: ProfitAnalysisRequest, productId?: number, activityId?: number) => {
    const params = new URLSearchParams();
    if (productId) params.set("product_id", String(productId));
    if (activityId) params.set("activity_id", String(activityId));
    return request<AnalysisRun>(`/analysis/run${params.size ? `?${params}` : ""}`, { method: "POST", body: JSON.stringify(payload) });
  },
  archiveAnalysis: (payload: ProfitAnalysisRequest, productId: number, activityId?: number) => {
    const params = new URLSearchParams({ product_id: String(productId) });
    if (activityId) params.set("activity_id", String(activityId));
    return request<AnalysisRun & { activity_id: number }>(`/analysis/archive?${params}`, { method: "POST", body: JSON.stringify(payload) });
  },
  analysis: (id: number) => request<{ result: AnalysisRun["result"]; scenarios: AnalysisRun["scenarios"]; recommendations?: string[] }>(`/analysis/${id}`),
  exportUrl: (id: number, format: "xlsx" | "csv") => `${API_URL}/export/${id}?format=${format}`,
};
