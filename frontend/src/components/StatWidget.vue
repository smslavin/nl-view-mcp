<script setup lang="ts">
import { computed } from "vue";
import { toStatValue } from "../chartData";
import type { WidgetSpec } from "../types";

const props = defineProps<{ spec: WidgetSpec }>();

const stat = computed(() => toStatValue(props.spec));
</script>

<template>
  <div class="flex h-full w-full flex-col items-center justify-center">
    <span class="text-4xl font-semibold text-slate-900">
      {{ stat.value ?? "—" }}
    </span>
    <span class="text-sm text-slate-500">{{ stat.unit }}</span>
  </div>
</template>
