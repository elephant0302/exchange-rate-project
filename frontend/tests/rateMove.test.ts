import { describe, expect, it } from "vitest";

import type { NewsItem } from "../src/api/types";
import { describeRateMove, newsForRateMove } from "../src/utils/rateMove";

const points = [
  { observed_at: "2026-08-13", value: 1400 },
  { observed_at: "2026-08-14", value: 1410 },
  { observed_at: "2026-08-17", value: 1390 },
];

function news(partial: Partial<NewsItem> & Pick<NewsItem, "id" | "published_at" | "direction">): NewsItem {
  return {
    title: `기사 ${partial.id}`,
    url: `https://example.com/${partial.id}`,
    source: "Example",
    collected_at: partial.published_at,
    pair: "USD_KRW",
    direction_label: "중립 또는 불명확",
    importance: "medium",
    importance_label: "보통",
    summary: "요약",
    keywords: [],
    is_mock: false,
    ...partial,
  };
}

describe("describeRateMove", () => {
  it("uses the previous and next dates around the clicked point", () => {
    const move = describeRateMove(points, "2026-08-14");
    expect(move.fromDate).toBe("2026-08-13");
    expect(move.toDate).toBe("2026-08-17");
    expect(move.changeValue).toBe(-10);
    expect(move.direction).toBe("down");
  });

  it("marks a rise when the next value is higher", () => {
    const move = describeRateMove(
      [
        { observed_at: "2026-08-13", value: 1400 },
        { observed_at: "2026-08-14", value: 1405 },
        { observed_at: "2026-08-15", value: 1420 },
      ],
      "2026-08-14",
    );
    expect(move.direction).toBe("up");
    expect(move.changeValue).toBe(20);
  });
});

describe("newsForRateMove", () => {
  it("prefers news whose direction matches a rate drop", () => {
    const items = [
      news({
        id: 1,
        published_at: "2026-08-14T01:00:00Z",
        direction: "krw_strong",
        title: "원화 강세 관련",
      }),
      news({
        id: 2,
        published_at: "2026-08-14T02:00:00Z",
        direction: "krw_weak",
        title: "원화 약세 관련",
      }),
      news({
        id: 3,
        published_at: "2026-07-01T01:00:00Z",
        direction: "krw_strong",
        title: "먼 과거 기사",
      }),
    ];
    const move = describeRateMove(points, "2026-08-14");
    const selected = newsForRateMove(items, move);
    expect(selected.map((item) => item.id)).toEqual([1]);
    expect(selected[0]?.title).toContain("원화 강세");
  });

  it("keeps same-window high-importance news with matching directional news", () => {
    const items = [
      news({
        id: 1,
        published_at: "2026-08-14T01:00:00Z",
        direction: "krw_weak",
        title: "달러 강세",
      }),
      news({
        id: 2,
        published_at: "2026-08-15T01:00:00Z",
        direction: "neutral",
        importance: "high",
        title: "연준 FOMC",
      }),
    ];
    const move = describeRateMove(
      [
        { observed_at: "2026-08-13", value: 1400 },
        { observed_at: "2026-08-14", value: 1410 },
        { observed_at: "2026-08-17", value: 1430 },
      ],
      "2026-08-14",
    );
    expect(newsForRateMove(items, move).map((item) => item.id)).toEqual([1, 2]);
  });
});
