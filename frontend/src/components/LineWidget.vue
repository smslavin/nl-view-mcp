<script setup lang="ts">
import { computed } from "vue";
import { Line } from "vue-chartjs";
import { toChartJsData } from "../chartData";
import type { WidgetSpec } from "../types";

const props = defineProps<{ spec: WidgetSpec }>();

const data = computed(() => toChartJsData(props.spec));
const options = { responsive: true, maintainAspectRatio: false };
</script>

<template>
  <div class="h-full w-full">
    <Line :data="data" :options="options" />
  </div>
</template>
