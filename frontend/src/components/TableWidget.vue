<script setup lang="ts">
import type { WidgetSpec } from "../types";

const props = defineProps<{ spec: WidgetSpec }>();
</script>

<template>
  <div class="h-full w-full overflow-auto">
    <table class="w-full border-collapse text-left text-sm">
      <thead>
        <tr class="border-b border-slate-200">
          <th
            v-for="col in props.spec.columns ?? []"
            :key="col.key"
            class="px-2 py-1.5 font-medium text-slate-500"
            :class="col.kind === 'number' ? 'text-right' : 'text-left'"
          >
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, i) in props.spec.rows ?? []"
          :key="i"
          class="border-b border-slate-100 last:border-0"
        >
          <td
            v-for="col in props.spec.columns ?? []"
            :key="col.key"
            class="max-w-[16ch] truncate px-2 py-1.5 text-slate-700"
            :class="[
              col.kind === 'number' ? 'text-right tabular-nums' : 'text-left',
              col.kind === 'code' ? 'font-mono text-xs' : '',
            ]"
            :title="col.kind === 'code' ? String(row[col.key] ?? '') : undefined"
          >
            {{ row[col.key] ?? "—" }}
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="(props.spec.rows ?? []).length === 0" class="py-6 text-center text-sm text-slate-400">
      No rows.
    </p>
  </div>
</template>
