<script setup lang="ts">
import { computed } from "vue";

import type { ResponseMeta } from "../api/types";
import { formatDateTime } from "../utils/format";
import StatusBadge from "./StatusBadge.vue";

const props = defineProps<{
  meta: ResponseMeta | null;
  isMock: boolean;
  collectionLabel: string;
  refreshing: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const tone = computed(() => {
  if (props.collectionLabel.includes("실패")) {
    return "fail";
  }
  if (props.isMock) {
    return "mock";
  }
  return "ok";
});
</script>

<template>
  <header class="flex flex-col gap-4 rounded-2xl border border-white/10 bg-[#05070B] px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
    <div>
      <p class="text-xs uppercase tracking-[0.24em] text-mute">경영정보 · 일별 환율</p>
      <h1 class="mt-1 text-xl font-semibold text-ink">FX Intelligence Dashboard</h1>
    </div>
    <div class="flex flex-wrap items-center gap-3 text-sm text-mute">
      <div>
        <p class="text-xs">데이터 출처</p>
        <p class="text-ink">{{ meta?.source || "수집 전" }}</p>
      </div>
      <div>
        <p class="text-xs">마지막 갱신</p>
        <p class="text-ink">{{ formatDateTime(meta?.last_updated_at) }}</p>
      </div>
      <StatusBadge :label="collectionLabel" :tone="tone" />
      <StatusBadge v-if="isMock" label="Mock 모드" tone="mock" />
      <button
        class="rounded-lg border border-white/10 bg-panel px-3 py-2 text-ink hover:border-actual/40"
        :disabled="refreshing"
        type="button"
        @click="emit('refresh')"
      >
        {{ refreshing ? "갱신 중..." : "새로고침" }}
      </button>
    </div>
  </header>
</template>
