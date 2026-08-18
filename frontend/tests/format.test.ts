import { describe, expect, it } from "vitest";

import {
  formatNumber,
  formatPct,
  formatSigned,
  movementArrow,
  movementText,
} from "../src/utils/format";

describe("format helpers", () => {
  it("formats numbers and empty values", () => {
    expect(formatNumber(1411.916)).toBe("1,411.92");
    expect(formatNumber(null)).toBe("—");
  });

  it("formats signed change and percent", () => {
    expect(formatSigned(12.5)).toBe("+12.50");
    expect(formatSigned(-3)).toBe("-3.00");
    expect(formatPct(0.0123)).toBe("+1.23%");
  });

  it("uses arrows and text together", () => {
    expect(movementArrow(1)).toBe("▲");
    expect(movementText(1)).toBe("상승");
    expect(movementArrow(-1)).toBe("▼");
    expect(movementText(-1)).toBe("하락");
    expect(movementArrow(0)).toBe("→");
  });
});
