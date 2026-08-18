<script setup lang="ts">
import { computed, onMounted, watch } from "vue";

import AppFooter from "../components/AppFooter.vue";
import AppHeader from "../components/AppHeader.vue";
import NewsPanel from "../components/NewsPanel.vue";
import RateChart from "../components/RateChart.vue";
import SummaryCards from "../components/SummaryCards.vue";
import { useDashboard } from "../composables/useDashboard";
import { PAIR_OPTIONS } from "../api/types";

const dashboard = useDashboard();
const unitLabel = computed(
  () =>
    dashboard.meta.value?.unit_label ||
    PAIR_OPTIONS.find((item) => item.value === dashboard.pair.value)?.unit ||
    "",
);

onMounted(() => {
  void dashboard.load();
});

watch(
  () => dashboard.selectedNewsId.value,
  (id) => {
    if (id === null) {
      return;
    }
    document.getElementById(`news-${id}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  },
);
</script>

<template>
  <div class="min-h-screen bg-black px-4 py-4 lg:px-6">
    <div class="mx-auto flex max-w-[1680px] flex-col gap-4">
      <AppHeader
        :meta="dashboard.meta.value"
        :is-mock="dashboard.isMock.value"
        :collection-label="dashboard.collectionLabel.value"
        :refreshing="dashboard.refreshing.value"
        @refresh="dashboard.refresh"
      />

      <div
        v-if="dashboard.loading.value && !dashboard.payload.value"
        class="card px-5 py-8 text-sm text-mute"
      >
        일별 환율과 관련 뉴스를 불러오는 중입니다.
      </div>

      <div v-else-if="dashboard.error.value" class="card border-up/30 px-5 py-4 text-sm text-up">
        {{ dashboard.error.value }}
      </div>

      <div
        v-if="dashboard.warnings.value.length"
        class="panel px-4 py-3 text-xs text-warn"
      >
        <p v-for="warning in dashboard.warnings.value" :key="warning">{{ warning }}</p>
      </div>

      <SummaryCards
        :latest="dashboard.latest.value"
        :forecast="dashboard.forecast.value"
        :unit-label="unitLabel"
      />

      <section class="overflow-hidden rounded-2xl border border-white/10 bg-[#05070B] px-4 py-4 lg:px-5">
        <div class="grid items-stretch gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(320px,0.9fr)]">
          <RateChart
            :pair="dashboard.pair.value"
            :period="dashboard.period.value"
            :unit-label="unitLabel"
            :model="dashboard.chartModel.value"
            :selected-news-id="dashboard.selectedNewsId.value"
            :news-limit="dashboard.newsLimit.value"
            :news-total="dashboard.allNews.value.length"
            @update:pair="dashboard.selectPair"
            @update:period="dashboard.selectPeriod"
            @update:news-limit="dashboard.setNewsLimit"
            @select-point="dashboard.selectChartPoint($event.date, $event.id)"
          />
          <NewsPanel
            :items="dashboard.news.value"
            :focused-items="dashboard.focusedNews.value"
            :markers="dashboard.chartModel.value.markers"
            :selected-news-id="dashboard.selectedNewsId.value"
            :selected-move="dashboard.selectedMove.value"
            :news-total="dashboard.allNews.value.length"
            @select="dashboard.selectNews"
            @clear="dashboard.clearNewsFocus"
          />
        </div>
      </section>

      <AppFooter
        :forecast="dashboard.forecast.value"
        :meta="dashboard.meta.value"
        :statuses="dashboard.statuses.value"
      />
    </div>
  </div>
</template>
