export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return new Intl.NumberFormat("ko-KR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

export function formatSigned(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatNumber(value, digits)}`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  return value.slice(0, 10);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function movementLabel(change: number | null | undefined): "up" | "down" | "flat" {
  if (change === null || change === undefined || change === 0) {
    return "flat";
  }
  return change > 0 ? "up" : "down";
}

export function movementText(change: number | null | undefined): string {
  const kind = movementLabel(change);
  if (kind === "up") {
    return "상승";
  }
  if (kind === "down") {
    return "하락";
  }
  return "보합";
}

export function movementArrow(change: number | null | undefined): string {
  const kind = movementLabel(change);
  if (kind === "up") {
    return "▲";
  }
  if (kind === "down") {
    return "▼";
  }
  return "→";
}
