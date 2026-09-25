import type { AnalysisRun, BootstrapData, HistoricalMetrics, HistoricalRow, HistoryItem, MerchantAccount, ParsedPromotion, PlatformConfig, PlatformConnection, Product, ProductInput, ProfitAnalysisRequest, ResearchReport } from "@/types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { credentials: "include", ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (response.status === 401 && !path.startsWith("/auth/")) window.dispatchEvent(new Event("crossprofit:unauthorized"));
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "服务暂时不可用" }));
    throw new Error(body.detail ?? `请求失败 (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<MerchantAccount>("/auth/me"),
  sendCode: (email: string, purpose: "register" | "login" | "reset") => request<{ sent: boolean }>("/auth/code", { method: "POST", body: JSON.stringify({ email, purpose }) }),
  register: (email: string, code: string, password: string) => request<MerchantAccount>("/auth/register", { method: "POST", body: JSON.stringify({ email, code, password }) }),
  login: (email: string, password: string) => request<MerchantAccount>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  codeLogin: (email: string, code: string) => request<MerchantAccount>("/auth/login/code", { method: "POST", body: JSON.stringify({ email, code }) }),
  resetPassword: (email: string, code: string, password: string) => request<MerchantAccount>("/auth/reset-password", { method: "POST", body: JSON.stringify({ email, code, password }) }),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  setLocale: (locale: "zh" | "en") => request<{ locale: string }>("/auth/locale", { method: "PUT", body: JSON.stringify({ locale }) }),
  platformCatalog: () => request<Array<{ id: string; name: string; region: string }>>("/platform-catalog"),
  connections: () => request<PlatformConnection[]>("/connections"),
  createConnection: (payload: { platform: string; label: string; shop_id?: string; app_key?: string; app_secret?: string; access_token?: string }) => request<PlatformConnection>("/connections", { method: "POST", body: JSON.stringify(payload) }),
  updateConnection: (id: number, payload: { platform: string; label: string; shop_id?: string; app_key?: string; app_secret?: string; access_token?: string }) => request<PlatformConnection>(`/connections/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteConnection: (id: number) => request<void>(`/connections/${id}`, { method: "DELETE" }),
  aiKeyStatus: () => request<{ configured: boolean }>("/ai/key"),
  saveAiKey: (api_key: string | null) => request<{ configured: boolean }>("/ai/key", { method: "PUT", body: JSON.stringify({ api_key }) }),
  historicalMetrics: () => request<HistoricalRow[]>("/historical-metrics"),
  addHistoricalMetric: (payload: Omit<HistoricalRow, "id">) => request<HistoricalRow>("/historical-metrics", { method: "POST", body: JSON.stringify(payload) }),
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
