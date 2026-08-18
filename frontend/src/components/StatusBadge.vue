<script setup lang="ts">
defineProps<{
  label: string;
  tone?: "ok" | "warn" | "mock" | "fail";
}>();
</script>

<template>
  <span
    class="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs"
    :class="{
      'border-ok/30 bg-ok/10 text-ok': tone === 'ok',
      'border-warn/30 bg-warn/10 text-warn': tone === 'warn' || tone === 'mock',
      'border-up/30 bg-up/10 text-up': tone === 'fail',
    }"
  >
    <span class="h-1.5 w-1.5 rounded-full bg-current" />
    {{ label }}
  </span>
</template>
