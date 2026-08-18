<script setup lang="ts">
import type { ForecastData, LatestRate } from "../api/types";
import { formatNumber, formatPct, formatSigned, movementArrow, movementText } from "../utils/format";

defineProps<{
  latest: LatestRate | null;
  forecast: ForecastData | null;
  unitLabel: string;
}>();

function toneClass(value: number | null | undefined): string {
  if (value === null || value === undefined || value === 0) {
    return "text-mute";
  }
  return value > 0 ? "text-up" : "text-down";
}
</script>

<template>
  <section class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
    <article class="rounded-xl border border-white/10 bg-[#05070B] p-4">
      <p class="text-xs text-mute">현재 환율 · 일별 종가</p>
      <p class="mono mt-2 text-3xl text-ink">{{ formatNumber(latest?.value) }}</p>
      <p class="mt-1 text-xs text-mute">{{ unitLabel }} · {{ latest?.observed_at || "데이터 없음" }}</p>
    </article>
    <article class="rounded-xl border border-white/10 bg-[#05070B] p-4">
      <p class="text-xs text-mute">전일 대비</p>
      <p class="mono mt-2 text-2xl" :class="toneClass(latest?.change_value)">
        <span aria-hidden="true">{{ movementArrow(latest?.change_value) }}</span>
        {{ formatSigned(latest?.change_value) }}
        <span class="ml-2 text-base">{{ formatPct(latest?.change_pct) }}</span>
      </p>
      <p class="mt-1 text-xs text-mute">{{ movementText(latest?.change_value) }} · 직전 영업일 대비</p>
    </article>
    <article class="rounded-xl border border-white/10 bg-[#05070B] p-4">
      <p class="text-xs text-mute">선택 기간 최고 / 최저 · 변동성</p>
      <p class="mono mt-2 text-lg text-ink">
        {{ formatNumber(latest?.period_high) }}
        <span class="text-mute"> / </span>
        {{ formatNumber(latest?.period_low) }}
      </p>
      <p class="mt-1 text-xs text-mute">
        최근 변동성(일별 수익률 표준편차)
        <span class="mono text-ink">{{ latest?.volatility == null ? "—" : formatPct(latest.volatility) }}</span>
      </p>
    </article>
    <article class="rounded-xl border border-white/10 bg-[#05070B] p-4">
      <p class="text-xs text-mute">30일 통계적 추정 중심값</p>
      <template v-if="forecast?.available && latest?.forecast_30d.available">
        <p class="mono mt-2 text-2xl text-forecast">
          {{ formatNumber(latest.forecast_30d.predicted_value) }}
        </p>
        <p class="mt-1 text-xs text-mute">
          범위 {{ formatNumber(latest.forecast_30d.lower_bound) }}
          ~ {{ formatNumber(latest.forecast_30d.upper_bound) }}
        </p>
      </template>
      <p v-else class="mt-2 text-sm text-mute">
        {{ forecast?.unavailable_reason || "예측 구간을 생성하지 못했습니다." }}
      </p>
    </article>
  </section>
</template>
