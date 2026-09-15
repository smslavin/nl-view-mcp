<script setup lang="ts">
import { computed } from "vue";
import { FLOW_NODE_H, FLOW_NODE_W, layoutFlow } from "../chartData";
import type { WidgetSpec } from "../types";

const props = defineProps<{ spec: WidgetSpec }>();

const layout = computed(() => layoutFlow(props.spec));

function edgePath(e: { from: { x: number; y: number }; to: { x: number; y: number } }) {
  const x1 = e.from.x + FLOW_NODE_W, y1 = e.from.y + FLOW_NODE_H / 2;
  const x2 = e.to.x, y2 = e.to.y + FLOW_NODE_H / 2;
  const mx = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
}

// Truncate long node labels rather than let them overflow the fixed-width
// node -- same rationale as mes-mcp's recall flow diagram this pattern is
// ported from.
function truncLabel(s: string, max = 15) {
  return s.length <= max ? s : `${s.slice(0, max - 1)}…`;
}
</script>

<template>
  <div class="flex h-full w-full items-center justify-center overflow-auto">
    <svg
      v-if="layout.nodes.length"
      :viewBox="`0 0 ${layout.width} ${layout.height}`"
      class="max-h-full max-w-full"
      role="img"
      :aria-label="`Flow: ${layout.nodes.map((n) => n.label).join(' -> ')}`"
    >
      <defs>
        <marker id="flow-arrow" markerWidth="7" markerHeight="7" refX="5.5" refY="2.5" orient="auto">
          <path d="M0,0 L5.5,2.5 L0,5 Z" fill="#94a3b8" />
        </marker>
      </defs>
      <path
        v-for="(e, i) in layout.edges"
        :key="i"
        :d="edgePath(e)"
        fill="none"
        stroke="#94a3b8"
        stroke-width="1.5"
        marker-end="url(#flow-arrow)"
      />
      <g v-for="n in layout.nodes" :key="n.id">
        <title>{{ n.label }}</title>
        <rect
          :x="n.x" :y="n.y" :width="FLOW_NODE_W" :height="FLOW_NODE_H" rx="7"
          fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.25"
        />
        <text
          :x="n.x + FLOW_NODE_W / 2" :y="n.y + FLOW_NODE_H / 2 + 4"
          text-anchor="middle" font-size="11" fill="#334155" font-family="ui-monospace, monospace"
        >{{ truncLabel(n.label) }}</text>
      </g>
    </svg>
    <p v-else class="text-sm text-slate-400">No routing data.</p>
  </div>
</template>
