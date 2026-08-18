import axios from "axios";

import type {
  CollectionStatus,
  DashboardPayload,
  Envelope,
  ForecastData,
  HistoryData,
  LatestRate,
  NewsItem,
  PairCode,
  PeriodKey,
} from "./types";

const baseURL = import.meta.env.VITE_API_BASE_URL || "";

export const http = axios.create({
  baseURL,
  timeout: 30000,
});

export async function fetchDashboard(
  pair: PairCode,
  period: PeriodKey,
): Promise<DashboardPayload> {
  const [latest, history, news, forecast, statuses] = await Promise.all([
    http.get<Envelope<LatestRate>>("/api/exchange-rates/latest", { params: { pair, period } }),
    http.get<Envelope<HistoryData>>("/api/exchange-rates/history", { params: { pair, period } }),
    http.get<Envelope<NewsItem[]>>("/api/news", { params: { pair, period, limit: 2000 } }),
    http.get<Envelope<ForecastData>>("/api/forecasts", { params: { pair, horizon: 30 } }),
    http.get<Envelope<CollectionStatus[]>>("/api/admin/status").catch(() => ({
      data: {
        data: [],
        meta: {
          source: "local",
          last_updated_at: null,
          unit: null,
          unit_label: null,
          frequency: "daily",
          is_mock: false,
          warnings: [],
          pair: null,
        },
      },
    })),
  ]);

  return {
    latest: latest.data,
    history: history.data,
    news: news.data,
    forecast: forecast.data,
    statuses: statuses.data,
  };
}

export async function refreshAll(): Promise<void> {
  await http.post("/api/admin/refresh");
}
