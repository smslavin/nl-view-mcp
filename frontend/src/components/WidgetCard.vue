<script setup lang="ts">
import { computed } from "vue";
import BarWidget from "./BarWidget.vue";
import FlowWidget from "./FlowWidget.vue";
import LineWidget from "./LineWidget.vue";
import StatWidget from "./StatWidget.vue";
import TableWidget from "./TableWidget.vue";
import type { BoardWidget } from "../types";

const props = defineProps<{ widget: BoardWidget }>();

const ROW_HEIGHT_PX = 60;

const gridStyle = computed(() => ({
  gridColumn: `span ${Math.min(props.widget.spec.size_hint.w, 12)} / span ${Math.min(props.widget.spec.size_hint.w, 12)}`,
  height: `${props.widget.spec.size_hint.h * ROW_HEIGHT_PX}px`,
}));

const component = computed(() => {
  switch (props.widget.spec.chart_type) {
    case "line":
      return LineWidget;
    case "bar":
      return BarWidget;
    case "table":
      return TableWidget;
    case "flow":
      return FlowWidget;
    default:
      return StatWidget;
  }
});
</script>

<template>
  <div
    :style="gridStyle"
    class="flex flex-col rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
  >
    <h3 class="mb-2 text-sm font-medium text-slate-700">{{ widget.spec.title }}</h3>
    <div class="min-h-0 flex-1">
      <component :is="component" :spec="widget.spec" />
    </div>
  </div>
</template>
