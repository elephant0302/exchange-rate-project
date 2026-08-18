<script setup lang="ts">
import { LineChart, ScatterChart } from "echarts/charts";
import {
  DataZoomComponent,
  GraphicComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  MarkPointComponent,
  TooltipComponent,
} from "echarts/components";
import { use } from "echarts/core";
import type { ECharts } from "echarts/core";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import type { PairCode, PeriodKey } from "../api/types";
import { NEWS_LIMIT_MAX, NEWS_LIMIT_MIN, PAIR_OPTIONS, PERIOD_OPTIONS } from "../api/types";
import { visibleNewsMarkers, type ChartModel } from "../utils/chart";

use([
  CanvasRenderer,
  LineChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent,
  GraphicComponent,
]);

const HISTORY_COLOR = "#3B82F6";
const FORECAST_COLOR = "#EF4444";

const props = defineProps<{
  pair: PairCode;
  period: PeriodKey;
  unitLabel: string;
  model: ChartModel;
  selectedNewsId: number | null;
  newsLimit: number;
  newsTotal: number;
}>();

const emit = defineEmits<{
  "update:pair": [value: PairCode];
  "update:period": [value: PeriodKey];
  "update:newsLimit": [value: number];
  "select-point": [payload: { date: string; id: number | null }];
}>();

const newsLimitDraft = ref(String(props.newsLimit));

watch(
  () => props.newsLimit,
  (value) => {
    newsLimitDraft.value = String(value);
  },
);

function commitNewsLimit() {
  const parsed = Number.parseInt(newsLimitDraft.value, 10);
  const next = Number.isFinite(parsed)
    ? Math.min(NEWS_LIMIT_MAX, Math.max(NEWS_LIMIT_MIN, parsed))
    : props.newsLimit;
  newsLimitDraft.value = String(next);
  emit("update:newsLimit", next);
}

function showAllNews() {
  const next = Math.min(NEWS_LIMIT_MAX, Math.max(NEWS_LIMIT_MIN, props.newsTotal || NEWS_LIMIT_MAX));
  newsLimitDraft.value = String(next);
  emit("update:newsLimit", next);
}

const el = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;
const hoveredDate = ref<string | null>(null);
const hasActual = computed(() => props.model.points.some((item) => item.actual !== null));
const hoveredMarkers = computed(() => visibleNewsMarkers(props.model.markers, hoveredDate.value));

function emitPoint(date: string, id: number | null = null) {
  emit("select-point", { date, id });
}

function newsScatterData() {
  return hoveredMarkers.value.map((marker) => ({
    value: [marker.date, marker.value],
    date: marker.date,
    id: marker.id,
    count: marker.count,
    labelText: `뉴스 ${marker.count}건`,
    itemStyle: {
      color: props.selectedNewsId === marker.id ? "#FBBF24" : "#F8FAFC",
      borderColor: HISTORY_COLOR,
      borderWidth: 2,
    },
  }));
}

function renderNewsDots() {
  if (!chart || !hasActual.value) {
    return;
  }
  chart.setOption({
    series: [
      {
        name: "사건 뉴스",
        data: newsScatterData(),
      },
    ],
  });
}

function setHoveredDate(next: string | null) {
  if (hoveredDate.value === next) {
    return;
  }
  hoveredDate.value = next;
  renderNewsDots();
}

function bindChartEvents(instance: ECharts) {
  instance.off("click");
  instance.off("updateAxisPointer");
  instance.off("globalout");
  instance.on("click", (params) => {
    const data = params.data as { date?: string; id?: number } | undefined;
    if (data?.date) {
      emitPoint(data.date, data.id ?? null);
      return;
    }
    if (typeof params.name === "string" && /^\d{4}-\d{2}-\d{2}$/.test(params.name)) {
      emitPoint(params.name, null);
    }
  });
  instance.on("updateAxisPointer", (event) => {
    const axesInfo = (event as { axesInfo?: Array<{ value?: string | number }> }).axesInfo;
    const value = axesInfo?.[0]?.value;
    setHoveredDate(value == null ? null : String(value));
  });
  instance.on("globalout", () => {
    setHoveredDate(null);
  });
}

function canDrawCanvas(): boolean {
  const probe = document.createElement("canvas");
  return Boolean(probe.getContext("2d"));
}

function ensureChart() {
  if (!el.value || !canDrawCanvas()) {
    return;
  }
  if (!chart) {
    chart = echarts.init(el.value, undefined, { renderer: "canvas" });
    bindChartEvents(chart);
  }
  render();
  chart.resize();
}

function render() {
  if (!chart || !hasActual.value) {
    return;
  }
  const dates = props.model.points.map((item) => item.date);
  const actual = props.model.points.map((item) => item.actual);
  const forecast = props.model.points.map((item) => item.forecast);
  const lower = props.model.points.map((item) => item.lower);
  const band = props.model.points.map((item) =>
    item.lower !== null && item.upper !== null ? item.upper - item.lower : null,
  );
  const boundaryIndex = props.model.boundaryDate
    ? dates.lastIndexOf(props.model.boundaryDate)
    : -1;
  const historyCenter = boundaryIndex > 0 ? dates[Math.floor(boundaryIndex / 2)] : dates[0];
  const forecastCenter =
    boundaryIndex >= 0 && boundaryIndex < dates.length - 1
      ? dates[Math.min(dates.length - 1, boundaryIndex + Math.ceil((dates.length - boundaryIndex) / 2))]
      : null;

  chart.setOption(
    {
      backgroundColor: "transparent",
      animationDuration: 400,
      legend: {
        data: ["환율 거동", "환율 예측구간", "예측 범위"],
        textStyle: { color: "#E5E7EB", fontSize: 13 },
        top: 4,
        itemWidth: 22,
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#0B0F16",
        borderColor: "#334155",
        textStyle: { color: "#F3F4F6" },
        formatter: (params: unknown) => {
          const items = Array.isArray(params) ? params : [params];
          const first = items[0] as { axisValue?: string; name?: string };
          const date = String(first?.axisValue || first?.name || "");
          const newsCount = props.model.markers.find((marker) => marker.date === date)?.count ?? 0;
          const lines = (items as Array<{ marker: string; seriesName: string; data: number | null }>)
            .filter((item) => item.seriesName !== "예측 하한" && item.seriesName !== "사건 뉴스" && item.data !== null)
            .map((item) => `${item.marker} ${item.seriesName}: ${item.data}`);
          if (newsCount > 0) {
            lines.push(`뉴스 ${newsCount}건`);
          }
          return [`${date}`, ...lines].join("<br/>");
        },
      },
      grid: { left: 64, right: 36, top: 72, bottom: 56 },
      dataZoom: [
        { type: "inside", start: 55, end: 100 },
        {
          type: "slider",
          start: 55,
          end: 100,
          height: 16,
          bottom: 12,
          borderColor: "#1f2937",
          fillerColor: "rgba(59,130,246,0.18)",
          handleStyle: { color: "#3B82F6" },
          textStyle: { color: "#94A3B8" },
        },
      ],
      xAxis: {
        type: "category",
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: "#64748B" } },
        axisTick: { show: false },
        axisLabel: { color: "#94A3B8" },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        scale: true,
        name: props.unitLabel,
        nameTextStyle: { color: "#94A3B8", padding: [0, 0, 0, 8] },
        axisLabel: { color: "#94A3B8" },
        axisLine: { show: true, lineStyle: { color: "#64748B" } },
        splitLine: { lineStyle: { color: "#1E293B", type: "dashed" } },
      },
      graphic: [
        historyCenter
          ? {
              type: "text",
              left: "28%",
              top: 38,
              style: {
                text: "환율 거동",
                fill: HISTORY_COLOR,
                fontSize: 18,
                fontWeight: 600,
              },
              z: 10,
            }
          : undefined,
        forecastCenter
          ? {
              type: "text",
              right: 48,
              top: 38,
              style: {
                text: "환율 예측구간",
                fill: FORECAST_COLOR,
                fontSize: 18,
                fontWeight: 600,
              },
              z: 10,
            }
          : undefined,
      ].filter(Boolean),
      series: [
        {
          name: "환율 거동",
          type: "line",
          data: actual,
          showSymbol: false,
          smooth: 0.15,
          lineStyle: { width: 3, color: HISTORY_COLOR },
          itemStyle: { color: HISTORY_COLOR },
          markLine: props.model.boundaryDate
            ? {
                symbol: "none",
                silent: true,
                label: {
                  show: true,
                  formatter: "현재",
                  color: "#E5E7EB",
                  fontSize: 11,
                },
                lineStyle: { type: "dashed", color: "#CBD5E1", width: 1.5 },
                data: [{ xAxis: props.model.boundaryDate }],
              }
            : undefined,
        },
        {
          name: "예측 하한",
          type: "line",
          data: lower,
          lineStyle: { opacity: 0 },
          stack: "band",
          symbol: "none",
          tooltip: { show: false },
        },
        {
          name: "예측 범위",
          type: "line",
          data: band,
          stack: "band",
          symbol: "none",
          areaStyle: { color: "rgba(239, 68, 68, 0.16)" },
          lineStyle: { opacity: 0 },
        },
        {
          name: "환율 예측구간",
          type: "line",
          data: forecast,
          showSymbol: false,
          smooth: 0.15,
          lineStyle: { width: 3, color: FORECAST_COLOR },
          itemStyle: { color: FORECAST_COLOR },
        },
        {
          name: "사건 뉴스",
          type: "scatter",
          z: 20,
          data: newsScatterData(),
          symbolSize: 16,
          emphasis: { scale: 1.35 },
          tooltip: { show: false },
          label: {
            show: true,
            formatter: (params: { data: { labelText: string } }) => params.data.labelText,
            color: "#F8FAFC",
            fontSize: 11,
            fontWeight: 600,
            position: "top",
            distance: 10,
            backgroundColor: "#111827",
            borderColor: "#334155",
            borderWidth: 1,
            borderRadius: 4,
            padding: [3, 7],
          },
        },
      ],
    },
    true,
  );
}

function handleResize() {
  chart?.resize();
}

onMounted(async () => {
  window.addEventListener("resize", handleResize);
  await nextTick();
  ensureChart();
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  chart?.dispose();
  chart = null;
});

watch(el, async (element) => {
  if (!element) {
    return;
  }
  await nextTick();
  ensureChart();
});

watch(
  () => [props.model, props.selectedNewsId, props.unitLabel, hasActual.value],
  async () => {
    await nextTick();
    ensureChart();
  },
  { deep: true },
);
</script>

<template>
  <section class="flex min-h-[72vh] flex-col bg-transparent">
    <div class="mb-3 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h2 class="text-base font-semibold text-ink">환율 추이 그래프 · 일별</h2>
        <p class="text-xs text-mute">파란 실선은 실제 환율, 빨간 실선은 통계적 예측입니다. 실시간 시세가 아닙니다. 단위: {{ unitLabel }}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <label class="flex items-center gap-2 rounded-lg border border-white/10 bg-[#111827] px-3 py-2 text-sm">
          <span class="whitespace-nowrap text-mute">뉴스 최신</span>
          <input
            v-model="newsLimitDraft"
            class="w-16 bg-transparent text-ink outline-none"
            type="number"
            :min="NEWS_LIMIT_MIN"
            :max="NEWS_LIMIT_MAX"
            data-testid="news-limit-input"
            @change="commitNewsLimit"
            @keydown.enter.prevent="commitNewsLimit"
          />
          <span class="whitespace-nowrap text-mute">건</span>
          <span class="whitespace-nowrap text-xs text-mute" data-testid="news-limit-count">
            / {{ newsTotal }}
          </span>
          <button
            type="button"
            class="whitespace-nowrap text-xs text-blue-300 hover:underline"
            data-testid="news-limit-all"
            @click="showAllNews"
          >
            전체
          </button>
        </label>
        <select
          class="rounded-lg border border-white/10 bg-[#111827] px-3 py-2 text-sm"
          :value="pair"
          data-testid="pair-select"
          @change="emit('update:pair', ($event.target as HTMLSelectElement).value as PairCode)"
        >
          <option v-for="option in PAIR_OPTIONS" :key="option.value" :value="option.value">
            {{ option.label }} · {{ option.unit }}
          </option>
        </select>
        <div class="flex rounded-lg border border-white/10 bg-[#111827] p-1">
          <button
            v-for="option in PERIOD_OPTIONS"
            :key="option.value"
            type="button"
            class="rounded-md px-2.5 py-1 text-xs"
            :class="period === option.value ? 'bg-blue-500/20 text-blue-300' : 'text-mute'"
            :data-testid="`period-${option.value}`"
            @click="emit('update:period', option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
    </div>
    <div class="relative h-[640px] w-full">
      <div
        v-if="!hasActual"
        class="absolute inset-0 z-10 flex items-center justify-center bg-black/70 text-sm text-mute"
        data-testid="empty-chart"
      >
        선택한 기간의 환율 데이터가 없습니다.
      </div>
      <div ref="el" class="h-full w-full" data-testid="chart-canvas" />
    </div>
    <p class="mt-2 text-xs text-mute">
      세로 점선은 실제와 예측의 경계입니다. 그래프에 커서를 올리면 그 날짜에 뉴스가 있을 때만 흰 점이 나타납니다. 점을 누르면 관련 뉴스가 오른쪽에 표시됩니다.
      예측값은 통계적 추정치이며 실제 환율과 다를 수 있습니다.
    </p>
  </section>
</template>
