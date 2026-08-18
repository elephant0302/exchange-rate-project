import { computed, ref } from "vue";

import { fetchDashboard, refreshAll } from "../api/client";
import type { CollectionStatus, DashboardPayload, PairCode, PeriodKey } from "../api/types";
import { NEWS_LIMIT_DEFAULT, NEWS_LIMIT_MAX, NEWS_LIMIT_MIN } from "../api/types";
import { buildChartModel, emptyChartModel } from "../utils/chart";
import { describeRateMove, newsForRateMove, type RateMove } from "../utils/rateMove";

export function useDashboard() {
  const pair = ref<PairCode>("USD_KRW");
  const period = ref<PeriodKey>("1Y");
  const newsLimit = ref(NEWS_LIMIT_DEFAULT);
  const loading = ref(true);
  const refreshing = ref(false);
  const error = ref<string | null>(null);
  const payload = ref<DashboardPayload | null>(null);
  const selectedNewsId = ref<number | null>(null);
  const selectedMove = ref<RateMove | null>(null);

  const latest = computed(() => payload.value?.latest.data ?? null);
  const history = computed(() => payload.value?.history.data ?? null);
  const allNews = computed(() => payload.value?.news.data ?? []);
  const news = computed(() => allNews.value.slice(0, newsLimit.value));
  const forecast = computed(() => payload.value?.forecast.data ?? null);
  const meta = computed(() => payload.value?.latest.meta ?? payload.value?.history.meta ?? null);
  const statuses = computed<CollectionStatus[]>(() => payload.value?.statuses.data ?? []);
  const warnings = computed(() => {
    const items = [
      ...(payload.value?.latest.meta.warnings ?? []),
      ...(payload.value?.news.meta.warnings ?? []),
      ...(payload.value?.forecast.meta.warnings ?? []),
    ];
    return [...new Set(items)];
  });
  const isMock = computed(
    () =>
      Boolean(meta.value?.is_mock) ||
      Boolean(payload.value?.news.meta.is_mock) ||
      Boolean(payload.value?.forecast.meta.is_mock),
  );
  const chartModel = computed(() =>
    payload.value
      ? buildChartModel(payload.value.history.data, payload.value.forecast.data, news.value)
      : emptyChartModel(),
  );
  const focusedNews = computed(() => {
    if (!selectedMove.value) {
      return news.value;
    }
    return newsForRateMove(news.value, selectedMove.value);
  });
  const hasHistory = computed(() => (history.value?.points.length ?? 0) > 0);
  const collectionLabel = computed(() => {
    const exchange = statuses.value.find((item) => item.job_name === "exchange");
    if (!exchange) {
      return isMock.value ? "Mock 데이터 사용 중" : "수집 상태 확인 중";
    }
    if (exchange.status === "failed") {
      return "데이터 수집 실패";
    }
    if (exchange.status === "mock" || exchange.is_mock) {
      return "Mock 데이터 사용 중";
    }
    return "일별 데이터 정상";
  });

  async function load() {
    loading.value = true;
    error.value = null;
    try {
      payload.value = await fetchDashboard(pair.value, period.value);
    } catch (err) {
      error.value = err instanceof Error ? err.message : "대시보드 데이터를 불러오지 못했습니다.";
    } finally {
      loading.value = false;
    }
  }

  async function refresh() {
    refreshing.value = true;
    error.value = null;
    try {
      await refreshAll();
      await load();
    } catch (err) {
      error.value = err instanceof Error ? err.message : "새로고침에 실패했습니다.";
    } finally {
      refreshing.value = false;
    }
  }

  function selectPair(next: PairCode) {
    pair.value = next;
    selectedNewsId.value = null;
    selectedMove.value = null;
    void load();
  }

  function selectPeriod(next: PeriodKey) {
    period.value = next;
    void load();
  }

  function setNewsLimit(next: number) {
    if (!Number.isFinite(next)) {
      return;
    }
    newsLimit.value = Math.min(NEWS_LIMIT_MAX, Math.max(NEWS_LIMIT_MIN, Math.round(next)));
  }

  function selectNews(id: number | null) {
    selectedNewsId.value = id;
  }

  function selectChartPoint(date: string, id: number | null = null) {
    const points = history.value?.points ?? [];
    const move = describeRateMove(points, date);
    selectedMove.value = move;
    const related = newsForRateMove(news.value, move);
    selectedNewsId.value = id && related.some((item) => item.id === id) ? id : related[0]?.id ?? null;
  }

  function clearNewsFocus() {
    selectedNewsId.value = null;
    selectedMove.value = null;
  }

  return {
    pair,
    period,
    newsLimit,
    allNews,
    loading,
    refreshing,
    error,
    payload,
    selectedNewsId,
    selectedMove,
    focusedNews,
    latest,
    history,
    news,
    forecast,
    meta,
    statuses,
    warnings,
    isMock,
    chartModel,
    hasHistory,
    collectionLabel,
    load,
    refresh,
    selectPair,
    selectPeriod,
    setNewsLimit,
    selectNews,
    selectChartPoint,
    clearNewsFocus,
  };
}
