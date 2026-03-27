export type TopItem = {
  name: string;
  value: number;
  percentage: number;
};

export type FlowItem = {
  flow: string;
  count: number;
  percentage: number;
};

export type PageEngagement = {
  page: string;
  views: number;
  clicks: number;
  avgScroll: number;
  exitRate: number;
};

export type AnalyticsSnapshot = {
  totalEvents: number;
  totalSessions: number;
  topPages: TopItem[];
  topProducts: TopItem[];
  abandonment: TopItem[];
  commonFlows: FlowItem[];
  pageEngagement: PageEngagement[];
  intentRate: number;
  additionalInsights: string[];
};

export type DatasetInfo = {
  columns: string[];
  total_rows: number;
  total_sessions: number;
  is_loaded: boolean;
};

export type AskResponse = {
  answer: string;
  interpretation: string;
  chart_data?: {
    chart_type: string;
    labels: string[];
    values: number[];
    label?: string;
  } | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const toTopPages = (items: Array<Record<string, unknown>>): TopItem[] =>
  items.map((item) => ({
    name: String(item.page ?? ""),
    value: Number(item.views ?? 0),
    percentage: Number(item.percentage ?? 0)
  }));

const toTopProducts = (items: Array<Record<string, unknown>>): TopItem[] =>
  items.map((item) => ({
    name: String(item.product ?? ""),
    value: Number(item.views ?? 0),
    percentage: Number(item.session_percentage ?? 0)
  }));

const toAbandonment = (items: Array<Record<string, unknown>>): TopItem[] =>
  items.map((item) => ({
    name: String(item.page ?? ""),
    value: Number(item.exit_count ?? 0),
    percentage: Number(item.exit_rate ?? 0)
  }));

const toFlows = (items: Array<Record<string, unknown>>): FlowItem[] =>
  items.map((item) => ({
    flow: Array.isArray(item.sequence) ? item.sequence.map(String).join(" → ") : "",
    count: Number(item.count ?? 0),
    percentage: Number(item.percentage ?? 0)
  }));

const toPageEngagement = (items: Array<Record<string, unknown>>): PageEngagement[] =>
  items.map((item) => ({
    page: String(item.page ?? ""),
    views: Number(item.total_events ?? 0),
    clicks: Number(item.avg_clicks ?? 0),
    avgScroll: Number(item.avg_scroll ?? 0),
    exitRate: 0
  }));

const buildInsights = (snapshot: AnalyticsSnapshot): string[] => {
  const insights: string[] = [];
  if (snapshot.topPages[0]) {
    insights.push(`La página con mayor tráfico es ${snapshot.topPages[0].name}.`);
  }
  if (snapshot.abandonment[0]) {
    insights.push(`Mayor abandono en ${snapshot.abandonment[0].name} (${snapshot.abandonment[0].percentage.toFixed(1)}%).`);
  }
  if (snapshot.intentRate > 0) {
    insights.push(`La intención de conversión actual es ${snapshot.intentRate.toFixed(1)}%.`);
  }
  return insights;
};

const safeFetch = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Error ${response.status} en ${path}`);
  }
  return response.json() as Promise<T>;
};

export const getDatasetInfo = async (): Promise<DatasetInfo> => safeFetch<DatasetInfo>("/api/dataset/info");

export const getDashboardSnapshot = async (): Promise<AnalyticsSnapshot> => {
  const dashboard = await safeFetch<Record<string, unknown>>("/api/dashboard");
  const summary = (dashboard.summary ?? {}) as Record<string, unknown>;
  const topPagesRaw = Array.isArray(dashboard.top_pages) ? (dashboard.top_pages as Array<Record<string, unknown>>) : [];
  const topProductsRaw = Array.isArray(dashboard.top_products) ? (dashboard.top_products as Array<Record<string, unknown>>) : [];
  const abandonmentRaw = Array.isArray(dashboard.abandono) ? (dashboard.abandono as Array<Record<string, unknown>>) : [];
  const flowsRaw = Array.isArray(dashboard.flujos) ? (dashboard.flujos as Array<Record<string, unknown>>) : [];
  const interaccionRaw = Array.isArray(dashboard.interaccion) ? (dashboard.interaccion as Array<Record<string, unknown>>) : [];

  const totalSessions = Number(summary.total_sessions ?? 0);
  const conversion = Array.isArray(dashboard.conversion) ? (dashboard.conversion as Array<Record<string, unknown>>) : [];
  const sessionsReached = conversion.reduce((acc, item) => acc + Number(item.sessions_reached ?? 0), 0);
  const intentRate = totalSessions > 0 ? Math.min(100, (sessionsReached / totalSessions) * 100) : 0;

  const snapshot: AnalyticsSnapshot = {
    totalEvents: Number(summary.total_events ?? 0),
    totalSessions,
    topPages: toTopPages(topPagesRaw),
    topProducts: toTopProducts(topProductsRaw),
    abandonment: toAbandonment(abandonmentRaw),
    commonFlows: toFlows(flowsRaw),
    pageEngagement: toPageEngagement(interaccionRaw),
    intentRate,
    additionalInsights: []
  };

  snapshot.additionalInsights = buildInsights(snapshot);
  return snapshot;
};

export const askCopilot = async (question: string): Promise<AskResponse> =>
  safeFetch<AskResponse>("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question })
  });

export const uploadDataset = async (
  recordingsFile: File,
  metricsFile?: File
): Promise<DatasetInfo> => {
  const formData = new FormData();
  formData.append("recordings_file", recordingsFile);
  if (metricsFile) formData.append("metrics_file", metricsFile);
  await safeFetch("/api/dataset/upload", {
    method: "POST",
    body: formData
  });
  return getDatasetInfo();
};
