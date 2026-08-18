import type { NewsItem } from "../api/types";

export type MoveDirection = "up" | "down" | "flat";

export interface RateObservation {
  observed_at: string;
  value: number;
}

export interface RateMove {
  pivotDate: string;
  fromDate: string | null;
  toDate: string | null;
  fromValue: number | null;
  toValue: number | null;
  changeValue: number | null;
  changePct: number | null;
  direction: MoveDirection;
}

const FLAT_EPS = 0.0001;

function publishedDay(item: NewsItem): string {
  return item.published_at.slice(0, 10);
}

function inRange(day: string, start: string, end: string): boolean {
  return day >= start && day <= end;
}

function shiftDay(day: string, days: number): string {
  const date = new Date(`${day}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function describeRateMove(points: RateObservation[], pivotDate: string): RateMove {
  const series = [...points].sort((left, right) => left.observed_at.localeCompare(right.observed_at));
  if (series.length === 0) {
    return {
      pivotDate,
      fromDate: null,
      toDate: null,
      fromValue: null,
      toValue: null,
      changeValue: null,
      changePct: null,
      direction: "flat",
    };
  }

  let index = series.findIndex((item) => item.observed_at === pivotDate);
  if (index < 0) {
    index = series.reduce((best, item, current) => {
      const bestGap = Math.abs(Date.parse(series[best].observed_at) - Date.parse(pivotDate));
      const currentGap = Math.abs(Date.parse(item.observed_at) - Date.parse(pivotDate));
      return currentGap < bestGap ? current : best;
    }, 0);
  }

  const current = series[index];
  const previous = series[index - 1] ?? null;
  const next = series[index + 1] ?? null;
  const from = previous ?? current;
  const to = next ?? current;
  const changeValue = to.value - from.value;
  const changePct = from.value === 0 ? null : changeValue / from.value;
  let direction: MoveDirection = "flat";
  if (changeValue > FLAT_EPS) {
    direction = "up";
  } else if (changeValue < -FLAT_EPS) {
    direction = "down";
  }

  return {
    pivotDate: current.observed_at,
    fromDate: from.observed_at,
    toDate: to.observed_at,
    fromValue: from.value,
    toValue: to.value,
    changeValue,
    changePct,
    direction,
  };
}

function importanceRank(item: NewsItem): number {
  if (item.importance === "high") {
    return 0;
  }
  if (item.importance === "medium") {
    return 1;
  }
  return 2;
}

function matchingDirection(direction: MoveDirection): string | null {
  if (direction === "up") {
    return "krw_weak";
  }
  if (direction === "down") {
    return "krw_strong";
  }
  return null;
}

export function newsForRateMove(items: NewsItem[], move: RateMove): NewsItem[] {
  const start = move.fromDate ?? shiftDay(move.pivotDate, -3);
  const end = move.toDate ?? shiftDay(move.pivotDate, 3);
  let windowItems = items.filter((item) => inRange(publishedDay(item), start, end));
  if (windowItems.length === 0) {
    windowItems = items.filter((item) =>
      inRange(publishedDay(item), shiftDay(move.pivotDate, -5), shiftDay(move.pivotDate, 5)),
    );
  }

  const wanted = matchingDirection(move.direction);
  const directional = wanted
    ? windowItems.filter((item) => item.direction === wanted)
    : [];
  const selected =
    directional.length > 0
      ? [
          ...directional,
          ...windowItems.filter(
            (item) => item.importance === "high" && !directional.some((match) => match.id === item.id),
          ),
        ]
      : windowItems;

  return [...selected].sort((left, right) => {
    const directionDelta =
      Number(wanted !== null && left.direction !== wanted) - Number(wanted !== null && right.direction !== wanted);
    if (directionDelta !== 0) {
      return directionDelta;
    }
    const importanceDelta = importanceRank(left) - importanceRank(right);
    if (importanceDelta !== 0) {
      return importanceDelta;
    }
    return right.published_at.localeCompare(left.published_at);
  });
}
