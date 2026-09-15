<script setup lang="ts">
import type { BoardWidget } from "../types";
import WidgetCard from "./WidgetCard.vue";

defineProps<{ widgets: BoardWidget[] }>();
</script>

<template>
  <div v-if="widgets.length === 0" class="py-16 text-center text-slate-400">
    Ask for a view to get started.
  </div>
  <div v-else class="grid grid-cols-12 gap-4">
    <WidgetCard v-for="widget in widgets" :key="widget.id" :widget="widget" />
  </div>
</template>
