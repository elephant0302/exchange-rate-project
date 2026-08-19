<script setup lang="ts">
import type { CollectionStatus, ForecastData, ResponseMeta } from "../api/types";
import { formatDate, formatDateTime, formatNumber } from "../utils/format";

defineProps<{
  forecast: ForecastData | null;
  meta: ResponseMeta | null;
  statuses: CollectionStatus[];
}>();
</script>

<template>
  <footer class="grid gap-4 rounded-2xl border border-white/10 bg-[#05070B] p-4 text-xs text-mute md:grid-cols-4">
    <div>
      <p class="text-ink">예측 모델</p>
      <p class="mt-1">{{ forecast?.model_name || "미생성" }}</p>
      <p>RW 벤치마크 + AR/Holt 결합, 구간은 GARCH(1,1)</p>
      <p>학습 구간 {{ formatDate(forecast?.trained_from) }} ~ {{ formatDate(forecast?.trained_to) }}</p>
      <p>
        검증 MAE {{ forecast?.mae == null ? "—" : formatNumber(forecast.mae, 3) }}
        · RMSE {{ forecast?.rmse == null ? "—" : formatNumber(forecast.rmse, 3) }}
      </p>
    </div>
    <div>
      <p class="text-ink">데이터 출처</p>
      <p class="mt-1">{{ meta?.source || "—" }}</p>
      <p>빈도: 일별 (영업일 기준, 실시간 시세 아님)</p>
    </div>
    <div>
      <p class="text-ink">최근 수집 상태</p>
      <p v-for="item in statuses" :key="item.job_name" class="mt-1">
        {{ item.job_name }} · {{ item.status }}
        <span v-if="item.last_success_at"> · {{ formatDateTime(item.last_success_at) }}</span>
      </p>
      <p v-if="!statuses.length">아직 수집 이력이 없습니다.</p>
      <p class="mt-1">뉴스 자동 수집은 60분마다 실행됩니다.</p>
    </div>
    <div>
      <p class="text-ink">면책</p>
      <p class="mt-1 leading-5">
        본 화면의 예측은 통계적 추정치이며 투자, 환헤지, 경영 의사결정의 확정 정보가 아닙니다.
        뉴스는 제목·링크·요약만 저장하며 원문 저작권은 각 언론사에 있습니다.
      </p>
    </div>
  </footer>
</template>
