<script setup lang="ts">
import { ref } from "vue";
import Board from "./components/Board.vue";
import { useBoard } from "./composables/useBoard";
import { buildView } from "./mcpClient";

const instruction = ref("");
const loading = ref(false);
const error = ref<string | null>(null);
const { widgets, addWidget } = useBoard();

async function submit() {
  const text = instruction.value.trim();
  if (!text || loading.value) return;

  loading.value = true;
  error.value = null;
  try {
    const spec = await buildView(text);
    addWidget(text, spec);
    instruction.value = "";
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-8">
    <h1 class="mb-1 text-xl font-semibold text-slate-900">nl-view-mcp</h1>
    <p class="mb-6 text-sm text-slate-500">
      Ask for a view in plain English -- e.g. "show me tank level trends for the last hour".
    </p>

    <form class="mb-6 flex gap-2" @submit.prevent="submit">
      <input
        v-model="instruction"
        type="text"
        placeholder="show me tank level trends for the last hour"
        class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      />
      <button
        type="submit"
        :disabled="loading"
        class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {{ loading ? "Building…" : "Build view" }}
      </button>
    </form>

    <p v-if="error" class="mb-6 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ error }}
    </p>

    <Board :widgets="widgets" />
  </div>
</template>
