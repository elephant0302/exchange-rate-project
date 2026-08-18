import { describe, expect, it } from "vitest";

import type { ForecastData, HistoryData, NewsItem } from "../src/api/types";
import { buildChartModel, newsForChartDate, visibleNewsMarkers } from "../src/utils/chart";

const history: HistoryData = {
  pair: "USD_KRW",
  points: [
    { observed_at: "2026-08-14", value: 1411.27 },
    { observed_at: "2026-08-17", value: 1411.91 },
  ],
  events: [],
};

const forecast: ForecastData = {
  available: true,
  unavailable_reason: null,
  pair: "USD_KRW",
  model_name: "Drift",
  horizon_days: 30,
  confidence_level: 0.95,
  trained_from: "2025-01-02",
  trained_to: "2026-08-17",
  mae: 4,
  rmse: 5,
  created_at: "2026-08-18T00:00:00Z",
  disclaimer: "통계적 추정치",
  points: [
    {
      target_at: "2026-08-18",
      predicted_value: 1412,
      lower_bound: 1400,
      upper_bound: 1424,
    },
  ],
};

const news: NewsItem[] = [
  {
    id: 9,
    title: "연준 관련 뉴스",
    url: "https://example.com/a",
    source: "Example",
    published_at: "2026-08-17T01:00:00Z",
    collected_at: "2026-08-17T02:00:00Z",
    pair: "USD_KRW",
    direction: "neutral",
    direction_label: "중립 또는 불명확",
    importance: "high",
    importance_label: "높음",
    summary: "관련 뉴스",
    keywords: ["연준"],
    is_mock: false,
  },
];

describe("buildChartModel", () => {
  it("keeps actual and forecast series on a shared date axis", () => {
    const model = buildChartModel(history, forecast, news);
    expect(model.points.map((item) => item.date)).toEqual([
      "2026-08-14",
      "2026-08-17",
      "2026-08-18",
    ]);
    expect(model.points[1]?.actual).toBe(1411.91);
    expect(model.points[1]?.forecast).toBe(1411.91);
    expect(model.points[2]?.forecast).toBe(1412);
    expect(model.points[2]?.lower).toBe(1400);
    expect(model.points[2]?.upper).toBe(1424);
    expect(model.boundaryDate).toBe("2026-08-17");
  });

  it("places news markers on the matching actual rate", () => {
    const model = buildChartModel(history, forecast, news);
    expect(model.markers).toEqual([
      {
        id: 9,
        date: "2026-08-17",
        value: 1411.91,
        title: "연준 관련 뉴스",
        label: "뉴스 1 · 1건",
        count: 1,
      },
    ]);
  });

  it("snaps weekend news onto the previous business-day point", () => {
    const weekendNews = [
      {
        ...news[0],
        id: 10,
        published_at: "2026-08-16T12:00:00Z",
        title: "주말 기사",
      },
    ];
    const model = buildChartModel(history, forecast, weekendNews);
    expect(model.markers[0]?.date).toBe("2026-08-14");
    expect(model.markers[0]?.value).toBe(1411.27);
    expect(newsForChartDate(weekendNews, model.markers, "2026-08-14")).toEqual([10]);
    expect(newsForChartDate(weekendNews, model.markers, "2026-08-17")).toEqual([]);
  });

  it("keeps one chart marker per business day", () => {
    const sameDayNews = [
      news[0],
      { ...news[0], id: 11, title: "같은 날 두 번째 기사" },
    ];
    const model = buildChartModel(history, forecast, sameDayNews);
    expect(model.markers).toHaveLength(1);
    expect(model.markers[0]?.date).toBe("2026-08-17");
    expect(model.markers[0]?.count).toBe(2);
  });

  it("shows news markers only for the hovered date", () => {
    const model = buildChartModel(history, forecast, news);
    expect(visibleNewsMarkers(model.markers, null)).toEqual([]);
    expect(visibleNewsMarkers(model.markers, "2026-08-14")).toEqual([]);
    expect(visibleNewsMarkers(model.markers, "2026-08-17").map((item) => item.id)).toEqual([9]);
  });
});
