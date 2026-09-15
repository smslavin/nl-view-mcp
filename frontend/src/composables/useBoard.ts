import { ref } from "vue";
import type { BoardWidget, WidgetSpec } from "../types";

/** The board accumulates one tile per successful instruction -- this is what
 * makes it feel like building a dashboard rather than issuing one-off
 * queries. Placement is left to the CSS grid; the server only ever supplies
 * a size hint, never a position. One board per call: App.vue only ever
 * calls this once, so there's no need for shared/module-level state. */
export function useBoard() {
  const widgets = ref<BoardWidget[]>([]);

  function addWidget(instruction: string, spec: WidgetSpec) {
    widgets.value.push({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      instruction,
      spec,
    });
  }

  function clear() {
    widgets.value = [];
  }

  return { widgets, addWidget, clear };
}
