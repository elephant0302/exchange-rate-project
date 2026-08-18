import type { ForecastData, HistoryData, NewsItem } from "../api/types";

export interface ChartPoint {
  date: string;
  actual: number | null;
  forecast: number | null;
  lower: number | null;
  upper: number | null;
}

export interface NewsMarker {
  id: number;
  date: string;
  value: number;
  title: string;
  label: string;
  count: number;
}

export interface ChartModel {
  points: ChartPoint[];
  markers: NewsMarker[];
  boundaryDate: string | null;
}

function nearestObservation(
  points: { observed_at: string; value: number }[],
  day: string,
): { date: string; value: number } | null {
  const exact = points.find((item) => item.observed_at === day);
  if (exact) {
    return { date: exact.observed_at, value: exact.value };
  }
  const previous = [...points].reverse().find((item) => item.observed_at <= day);
  if (previous) {
    return { date: previous.observed_at, value: previous.value };
  }
  return points[0] ? { date: points[0].observed_at, value: points[0].value } : null;
}

export function visibleNewsMarkers(markers: NewsMarker[], hoveredDate: string | null): NewsMarker[] {
  if (!hoveredDate) {
    return [];
  }
  return markers.filter((marker) => marker.date === hoveredDate);
}

export function newsForChartDate(
  items: { id: number }[],
  markers: NewsMarker[],
  date: string | null,
): number[] {
  if (!date) {
    return items.map((item) => item.id);
  }
  return markers.filter((marker) => marker.date === date).map((marker) => marker.id);
}

export function buildChartModel(
  history: HistoryData | null,
  forecast: ForecastData | null,
  news: NewsItem[],
): ChartModel {
  const actuals = history?.points ?? [];
  const forecasts = forecast?.available ? forecast.points : [];
  const dates = [
    ...actuals.map((item) => item.observed_at),
    ...forecasts.map((item) => item.target_at),
  ];
  const uniqueDates = [...new Set(dates)].sort();
  const actualMap = new Map(actuals.map((item) => [item.observed_at, item.value]));
  const forecastMap = new Map(
    forecasts.map((item) => [item.target_at, item]),
  );

  const points: ChartPoint[] = uniqueDates.map((day) => {
    const forecastPoint = forecastMap.get(day);
    return {
      date: day,
      actual: actualMap.get(day) ?? null,
      forecast: forecastPoint?.predicted_value ?? null,
      lower: forecastPoint?.lower_bound ?? null,
      upper: forecastPoint?.upper_bound ?? null,
    };
  });

  const lastActual = actuals.at(-1);
  if (lastActual) {
    const boundary = points.find((item) => item.date === lastActual.observed_at);
    if (boundary) {
      boundary.forecast = lastActual.value;
      const firstForecast = forecasts[0];
      if (firstForecast) {
        boundary.lower = firstForecast.lower_bound;
        boundary.upper = firstForecast.upper_bound;
      }
    }
  }

  const mapped = news
    .map((item) => {
      const day = item.published_at.slice(0, 10);
      const observation = nearestObservation(actuals, day);
      if (observation === null) {
        return null;
      }
      return {
        id: item.id,
        date: observation.date,
        value: observation.value,
        title: item.title,
      };
    })
    .filter((item): item is { id: number; date: string; value: number; title: string } => item !== null)
    .sort((left, right) => left.date.localeCompare(right.date) || left.id - right.id);

  const counts = new Map<string, number>();
  for (const item of mapped) {
    counts.set(item.date, (counts.get(item.date) ?? 0) + 1);
  }

  const seenDates = new Set<string>();
  const markers: NewsMarker[] = mapped
    .filter((item) => {
      if (seenDates.has(item.date)) {
        return false;
      }
      seenDates.add(item.date);
      return true;
    })
    .map((item, index) => {
      const count = counts.get(item.date) ?? 1;
      return {
        ...item,
        count,
        label: `뉴스 ${index + 1} · ${count}건`,
      };
    });

  return {
    points,
    markers,
    boundaryDate: lastActual?.observed_at ?? null,
  };
}

export function emptyChartModel(): ChartModel {
  return { points: [], markers: [], boundaryDate: null };
}
