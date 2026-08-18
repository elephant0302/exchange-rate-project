import { mount, flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DashboardPayload } from "../src/api/types";
import DashboardView from "../src/views/DashboardView.vue";

const fetchDashboard = vi.fn();
const refreshAll = vi.fn();

vi.mock("../src/api/client", () => ({
  fetchDashboard: (...args: unknown[]) => fetchDashboard(...args),
  refreshAll: (...args: unknown[]) => refreshAll(...args),
}));

function payload(overrides: Partial<DashboardPayload> = {}): DashboardPayload {
  const meta = {
    source: "Frankfurter (ECB 일별 환율)",
    last_updated_at: "2026-08-17T16:00:00Z",
    unit: "KRW/USD",
    unit_label: "1달러당 원화",
    frequency: "daily",
    is_mock: false,
    warnings: [],
    pair: "USD_KRW",
  };
  return {
    latest: {
      data: {
        pair: "USD_KRW",
        observed_at: "2026-08-17",
        value: 1411.91,
        previous_value: 1411.27,
        change_value: 0.64,
        change_pct: 0.00045,
        period_high: 1500,
        period_low: 1400,
        volatility: 0.01,
        forecast_30d: {
          available: true,
          predicted_value: 1405,
          lower_bound: 1370,
          upper_bound: 1440,
          model_name: "Drift",
          horizon_days: 30,
        },
      },
      meta,
    },
    history: {
      data: {
        pair: "USD_KRW",
        points: [
          { observed_at: "2026-08-14", value: 1411.27 },
          { observed_at: "2026-08-17", value: 1411.91 },
        ],
        events: [],
      },
      meta,
    },
    news: {
      data: [
        {
          id: 1,
          title: "연준 관련 기사",
          url: "https://www.federalreserve.gov/monetarypolicy/fomc.htm",
          source: "Fed",
          published_at: "2026-08-17T01:00:00Z",
          collected_at: "2026-08-17T02:00:00Z",
          pair: "USD_KRW",
          direction: "neutral",
          direction_label: "중립 또는 불명확",
          importance: "high",
          importance_label: "높음",
          summary: "해당 시점의 관련 뉴스",
          keywords: ["연준"],
          is_mock: false,
        },
      ],
      meta: { ...meta, source: "RSS" },
    },
    forecast: {
      data: {
        available: true,
        unavailable_reason: null,
        pair: "USD_KRW",
        model_name: "Drift",
        horizon_days: 30,
        confidence_level: 0.95,
        trained_from: "2025-01-02",
        trained_to: "2026-08-17",
        mae: 4.2,
        rmse: 5.1,
        created_at: "2026-08-18T00:00:00Z",
        disclaimer: "통계적 추정치이며 실제 환율과 다를 수 있습니다.",
        points: [
          {
            target_at: "2026-08-18",
            predicted_value: 1412,
            lower_bound: 1400,
            upper_bound: 1424,
          },
        ],
      },
      meta,
    },
    statuses: {
      data: [
        {
          job_name: "exchange",
          status: "success",
          source: "Frankfurter (ECB 일별 환율)",
          message: "ok",
          is_mock: false,
          last_run_at: "2026-08-17T16:00:00Z",
          last_success_at: "2026-08-17T16:00:00Z",
        },
      ],
      meta,
    },
    ...overrides,
  };
}

describe("DashboardView", () => {
  beforeEach(() => {
    fetchDashboard.mockReset();
    refreshAll.mockReset();
    fetchDashboard.mockResolvedValue(payload());
  });

  it("renders headline, source and latest rate", async () => {
    const wrapper = mount(DashboardView);
    await flushPromises();
    expect(wrapper.text()).toContain("FX Intelligence Dashboard");
    expect(wrapper.text()).toContain("Frankfurter (ECB 일별 환율)");
    expect(wrapper.text()).toContain("1,411.91");
    expect(wrapper.text()).toContain("1달러당 원화");
    expect(wrapper.text()).toContain("일별 데이터 정상");
  });

  it("changes currency and period", async () => {
    const wrapper = mount(DashboardView);
    await flushPromises();
    await wrapper.get('[data-testid="pair-select"]').setValue("EUR_KRW");
    await flushPromises();
    expect(fetchDashboard).toHaveBeenLastCalledWith("EUR_KRW", "1Y");

    await wrapper.get('[data-testid="period-3M"]').trigger("click");
    await flushPromises();
    expect(fetchDashboard).toHaveBeenLastCalledWith("EUR_KRW", "3M");
  });

  it("shows a loading state before data arrives", async () => {
    fetchDashboard.mockImplementation(() => new Promise(() => undefined));
    const wrapper = mount(DashboardView);
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("불러오는 중");
  });

  it("shows an error state when the API fails", async () => {
    fetchDashboard.mockRejectedValue(new Error("network down"));
    const wrapper = mount(DashboardView);
    await flushPromises();
    expect(wrapper.text()).toContain("network down");
  });

  it("shows an empty chart when there is no history", async () => {
    fetchDashboard.mockResolvedValue(
      payload({
        history: {
          data: { pair: "USD_KRW", points: [], events: [] },
          meta: payload().history.meta,
        },
      }),
    );
    const wrapper = mount(DashboardView);
    await flushPromises();
    expect(wrapper.get('[data-testid="empty-chart"]').text()).toContain("데이터가 없습니다");
  });

  it("limits displayed news to the selected latest count", async () => {
    const extra = payload();
    extra.news.data = [
      extra.news.data[0],
      {
        ...extra.news.data[0],
        id: 2,
        title: "두 번째 뉴스",
        url: "https://example.com/second",
        published_at: "2026-08-16T01:00:00Z",
      },
    ];
    fetchDashboard.mockResolvedValue(extra);
    const wrapper = mount(DashboardView);
    await flushPromises();
    expect(wrapper.get('[data-testid="news-scroll"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="news-count"]').text()).toContain("표시 2건");
    expect(wrapper.findAll('[data-testid="news-card"]')).toHaveLength(2);
    await wrapper.get('[data-testid="news-limit-input"]').setValue("1");
    await wrapper.get('[data-testid="news-limit-input"]').trigger("change");
    expect(wrapper.findAll('[data-testid="news-card"]')).toHaveLength(1);
  });

  it("renders news original links with security attributes", async () => {
    const wrapper = mount(DashboardView);
    await flushPromises();
    const link = wrapper.get('a[href="https://www.federalreserve.gov/monetarypolicy/fomc.htm"]');
    expect(link.attributes("target")).toBe("_blank");
    expect(link.attributes("rel")).toBe("noopener noreferrer");
    expect(link.text()).toContain("원문 보기");
  });

  it("shows mock badge when backend reports mock data", async () => {
    const mockPayload = payload();
    mockPayload.latest.meta.is_mock = true;
    mockPayload.latest.meta.warnings = ["현재 표시 중인 환율은 Mock 데이터이며 실제 시장 환율이 아닙니다."];
    mockPayload.statuses.data[0] = {
      ...mockPayload.statuses.data[0],
      status: "mock",
      is_mock: true,
    };
    fetchDashboard.mockResolvedValueOnce(mockPayload);
    const wrapper = mount(DashboardView);
    await flushPromises();
    expect(wrapper.text()).toContain("Mock 모드");
    expect(wrapper.text()).toContain("Mock 데이터 사용 중");
  });
});
