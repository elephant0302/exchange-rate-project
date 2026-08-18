export type PairCode = "USD_KRW" | "EUR_KRW" | "JPY_KRW" | "CNY_KRW";
export type PeriodKey = "1M" | "3M" | "6M" | "1Y" | "ALL";

export interface ResponseMeta {
  source: string;
  last_updated_at: string | null;
  unit: string | null;
  unit_label: string | null;
  frequency: string;
  is_mock: boolean;
  warnings: string[];
  pair: string | null;
}

export interface Envelope<T> {
  data: T;
  meta: ResponseMeta;
}

export interface Indicator {
  id: number;
  code: PairCode;
  name: string;
  category: string;
  unit: string;
  unit_label: string;
  frequency: string;
  source: string;
}

export interface LatestForecastSummary {
  available: boolean;
  predicted_value: number | null;
  lower_bound: number | null;
  upper_bound: number | null;
  model_name: string | null;
  horizon_days: number | null;
}

export interface LatestRate {
  pair: PairCode;
  observed_at: string | null;
  value: number | null;
  previous_value: number | null;
  change_value: number | null;
  change_pct: number | null;
  period_high: number | null;
  period_low: number | null;
  volatility: number | null;
  forecast_30d: LatestForecastSummary;
}

export interface RatePoint {
  observed_at: string;
  value: number;
}

export interface EventMarker {
  id: number;
  published_at: string;
  title: string;
  importance: string;
  direction: string;
}

export interface HistoryData {
  pair: PairCode;
  points: RatePoint[];
  events: EventMarker[];
}

export interface NewsItem {
  id: number;
  title: string;
  url: string;
  source: string;
  published_at: string;
  collected_at: string;
  pair: string | null;
  direction: string;
  direction_label: string;
  importance: string;
  importance_label: string;
  summary: string;
  keywords: string[];
  is_mock: boolean;
}

export interface ForecastPoint {
  target_at: string;
  predicted_value: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastData {
  available: boolean;
  unavailable_reason: string | null;
  pair: PairCode;
  model_name: string | null;
  horizon_days: number;
  confidence_level: number | null;
  trained_from: string | null;
  trained_to: string | null;
  mae: number | null;
  rmse: number | null;
  created_at: string | null;
  disclaimer: string;
  points: ForecastPoint[];
}

export interface CollectionStatus {
  job_name: string;
  status: string;
  source: string;
  message: string;
  is_mock: boolean;
  last_run_at: string | null;
  last_success_at: string | null;
}

export interface DashboardPayload {
  latest: Envelope<LatestRate>;
  history: Envelope<HistoryData>;
  news: Envelope<NewsItem[]>;
  forecast: Envelope<ForecastData>;
  statuses: Envelope<CollectionStatus[]>;
}

export const PAIR_OPTIONS: { value: PairCode; label: string; unit: string }[] = [
  { value: "USD_KRW", label: "USD/KRW", unit: "1달러당 원화" },
  { value: "EUR_KRW", label: "EUR/KRW", unit: "1유로당 원화" },
  { value: "JPY_KRW", label: "JPY/KRW", unit: "100엔당 원화" },
  { value: "CNY_KRW", label: "CNY/KRW", unit: "1위안당 원화" },
];

export const NEWS_LIMIT_MIN = 1;
export const NEWS_LIMIT_MAX = 2000;
export const NEWS_LIMIT_DEFAULT = 200;

export const PERIOD_OPTIONS: { value: PeriodKey; label: string }[] = [
  { value: "1M", label: "1개월" },
  { value: "3M", label: "3개월" },
  { value: "6M", label: "6개월" },
  { value: "1Y", label: "1년" },
  { value: "ALL", label: "전체" },
];
