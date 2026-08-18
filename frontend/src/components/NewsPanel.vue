<script setup lang="ts">
import { computed } from "vue";

import type { NewsItem } from "../api/types";
import type { NewsMarker } from "../utils/chart";
import type { RateMove } from "../utils/rateMove";
import { formatDateTime, formatPct, formatSigned, movementArrow, movementText } from "../utils/format";

const props = defineProps<{
  items: NewsItem[];
  focusedItems: NewsItem[];
  markers: NewsMarker[];
  selectedNewsId: number | null;
  selectedMove: RateMove | null;
  newsTotal: number;
}>();

const emit = defineEmits<{
  select: [id: number];
  clear: [];
}>();

const numbered = computed(() => {
  const labels = new Map(props.markers.map((marker) => [marker.id, marker.label]));
  return props.focusedItems.map((item, index) => ({
    ...item,
    label: labels.get(item.id) ?? `뉴스 ${index + 1}`,
  }));
});

const moveTone = computed(() => {
  if (!props.selectedMove || props.selectedMove.direction === "flat") {
    return "text-mute";
  }
  return props.selectedMove.direction === "up" ? "text-up" : "text-down";
});

function directionClass(direction: string): string {
  if (direction === "krw_weak") {
    return "border-up/30 bg-up/10 text-up";
  }
  if (direction === "krw_strong") {
    return "border-down/30 bg-down/10 text-down";
  }
  return "border-white/10 bg-white/5 text-mute";
}
</script>

<template>
  <aside class="flex h-[min(760px,80vh)] min-h-0 flex-col border-l border-white/10 pl-0 xl:pl-5">
    <div class="mb-3 shrink-0">
      <h2 class="text-base font-semibold text-ink">
        관련 뉴스
        <span class="ml-2 text-sm font-normal text-mute" data-testid="news-count">
          {{ selectedMove ? `이 구간 ${focusedItems.length}건` : `표시 ${items.length}건` }}
          <template v-if="!selectedMove && newsTotal > items.length"> · 수집 {{ newsTotal }}건</template>
        </span>
      </h2>
      <template v-if="selectedMove">
        <p class="mt-1 text-xs text-mute">
          구간 {{ selectedMove.fromDate || "—" }} → {{ selectedMove.toDate || "—" }}
        </p>
        <p class="mt-1 text-sm font-medium" :class="moveTone">
          <span aria-hidden="true">{{ movementArrow(selectedMove.changeValue) }}</span>
          환율 {{ movementText(selectedMove.changeValue) }}
          {{ formatSigned(selectedMove.changeValue) }}
          ({{ formatPct(selectedMove.changePct) }})
        </p>
        <p class="mt-1 text-xs text-mute">
          이 등락과 방향이 맞는, 영향 가능성이 있는 뉴스입니다. 환율이 움직인 원인으로 단정하지 않습니다.
        </p>
        <button
          type="button"
          class="mt-2 text-xs text-blue-300 hover:underline"
          @click="emit('clear')"
        >
          전체 뉴스 {{ items.length }}건 다시 보기
        </button>
      </template>
      <p v-else class="text-xs text-mute">
        최신 {{ items.length }}건을 표시합니다. 그래프에 커서를 올리면 뉴스가 있는 날짜에 흰 점이 나타나고, 누르면 관련 뉴스가 여기에 표시됩니다.
      </p>
    </div>
    <div v-if="!numbered.length" class="flex flex-1 items-center justify-center text-sm text-mute">
      {{ selectedMove ? "이 등락 구간에 연결할 뉴스가 없습니다." : "표시할 뉴스가 없습니다." }}
    </div>
    <div
      v-else
      class="news-scroll min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain scroll-smooth pr-2"
      data-testid="news-scroll"
    >
      <article
        v-for="item in numbered"
        :id="`news-${item.id}`"
        :key="item.id"
        class="cursor-pointer rounded-lg border p-3"
        :class="selectedNewsId === item.id ? 'border-amber-400 bg-amber-400/10' : 'border-white/10 bg-[#111827]'"
        data-testid="news-card"
        @click="emit('select', item.id)"
      >
        <div class="mb-2 flex flex-wrap items-center gap-2 text-[11px]">
          <span class="rounded-full border border-blue-400/40 bg-blue-500/10 px-2 py-0.5 text-blue-200">
            {{ item.label }}
          </span>
          <span class="rounded-full border px-2 py-0.5" :class="directionClass(item.direction)">
            {{ item.direction_label }}
          </span>
          <span class="rounded-full border border-white/10 px-2 py-0.5 text-mute">
            중요도 {{ item.importance_label }}
          </span>
          <span v-if="item.is_mock" class="rounded-full border border-warn/30 px-2 py-0.5 text-warn">
            Mock
          </span>
        </div>
        <h3 class="text-sm leading-5 text-ink">{{ item.title }}</h3>
        <p class="mt-1 text-xs text-mute">{{ item.source }} · {{ formatDateTime(item.published_at) }}</p>
        <p class="mt-2 text-xs leading-5 text-slate-300">{{ item.summary }}</p>
        <a
          class="mt-3 inline-flex text-xs text-blue-300 hover:underline"
          :href="item.url"
          target="_blank"
          rel="noopener noreferrer"
          @click.stop
        >
          원문 보기
        </a>
      </article>
    </div>
  </aside>
</template>
