import type { WidgetSpec } from "./types";

// A brand-neutral placeholder palette -- swap for real brand colors later.
const SERIES_COLORS = ["#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed"];

export interface ChartJsData {
  labels: (number | string)[];
  datasets: {
    label: string;
    data: (number | null)[];
    borderColor: string;
    backgroundColor: string;
  }[];
}

/** The widget spec has no semantic type for a point's x value -- "line"
 * charts happen to always use Unix-seconds timestamps and "bar" charts
 * categorical strings, but nothing in the schema says so. Formatting time
 * labels here is a client-side guess keyed on chart_type, not a real type;
 * see README findings. */
function formatLabel(x: number | string, chartType: WidgetSpec["chart_type"]): string {
  if (chartType === "line" && typeof x === "number") {
    return new Date(x * 1000).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
    });
  }
  return String(x);
}

/** Pure transform from a widget spec's series into Chart.js's {labels, datasets}
 * shape. Kept independent of any Vue/Chart.js runtime so it's directly
 * unit-testable. Only meaningful for chart_type "line" | "bar". */
export function toChartJsData(spec: WidgetSpec): ChartJsData {
  const seriesList = spec.series ?? [];
  const labels = seriesList[0]?.points.map((p) => formatLabel(p.x, spec.chart_type)) ?? [];

  return {
    labels,
    datasets: seriesList.map((series, i) => {
      const color = SERIES_COLORS[i % SERIES_COLORS.length];
      return {
        label: series.unit ? `${series.name} (${series.unit})` : series.name,
        data: series.points.map((p) => p.y),
        borderColor: color,
        backgroundColor: color,
      };
    }),
  };
}

/** For chart_type "stat": the single value + unit to show as a big number. */
export function toStatValue(spec: WidgetSpec): { value: number | null; unit: string } {
  const series = spec.series?.[0];
  const point = series?.points[0];
  return { value: point?.y ?? null, unit: series?.unit ?? "" };
}

// --- flow: layered DAG layout ---------------------------------------------------

export interface FlowLayoutNode {
  id: string;
  label: string;
  layer: number;
  x: number;
  y: number;
}
export interface FlowLayoutEdge {
  from: FlowLayoutNode;
  to: FlowLayoutNode;
}
export interface FlowLayout {
  nodes: FlowLayoutNode[];
  edges: FlowLayoutEdge[];
  width: number;
  height: number;
}

const FLOW_COL_W = 120;
const FLOW_COL_GAP = 56;
const FLOW_ROW_H = 34;
const FLOW_ROW_GAP = 14;
const FLOW_PAD = 12;

/** Generic longest-path layering for a DAG: a node with no incoming edge is
 * layer 0; every other node's layer is one past its deepest predecessor.
 * Works for any node/edge shape the spec sends -- a straight chain lays out
 * as one node per layer, a real branch (two edges out of the same node)
 * puts both children in the same next layer, stacked. */
export function layoutFlow(spec: WidgetSpec): FlowLayout {
  const nodes = spec.nodes ?? [];
  const edges = spec.edges ?? [];
  if (nodes.length === 0) return { nodes: [], edges: [], width: 0, height: 0 };

  const incoming = new Map<string, string[]>();
  for (const n of nodes) incoming.set(n.id, []);
  for (const e of edges) incoming.get(e.to)?.push(e.from);

  const layerById = new Map<string, number>();
  function layerOf(id: string, seen: Set<string> = new Set()): number {
    if (layerById.has(id)) return layerById.get(id)!;
    if (seen.has(id)) return 0; // cycle guard -- not expected, but don't hang
    seen.add(id);
    const preds = incoming.get(id) ?? [];
    const layer = preds.length === 0 ? 0 : Math.max(...preds.map((p) => layerOf(p, seen) + 1));
    layerById.set(id, layer);
    return layer;
  }
  for (const n of nodes) layerOf(n.id);

  const maxLayer = Math.max(...[...layerById.values()]);
  const byLayer: string[][] = Array.from({ length: maxLayer + 1 }, () => []);
  for (const n of nodes) byLayer[layerById.get(n.id)!]!.push(n.id);

  const maxRows = Math.max(...byLayer.map((l) => l.length));
  const height = FLOW_PAD * 2 + maxRows * FLOW_ROW_H + (maxRows - 1) * FLOW_ROW_GAP;
  const width = FLOW_PAD * 2 + byLayer.length * FLOW_COL_W + (byLayer.length - 1) * FLOW_COL_GAP;

  const byId = new Map<string, FlowLayoutNode>();
  const laidOutNodes: FlowLayoutNode[] = [];
  const labelById = new Map(nodes.map((n) => [n.id, n.label]));
  byLayer.forEach((ids, layer) => {
    const x = FLOW_PAD + layer * (FLOW_COL_W + FLOW_COL_GAP);
    const layerH = ids.length * FLOW_ROW_H + (ids.length - 1) * FLOW_ROW_GAP;
    const yOffset = (height - layerH) / 2;
    ids.forEach((id, i) => {
      const node: FlowLayoutNode = {
        id, label: labelById.get(id) ?? id, layer,
        x, y: yOffset + i * (FLOW_ROW_H + FLOW_ROW_GAP),
      };
      byId.set(id, node);
      laidOutNodes.push(node);
    });
  });

  const laidOutEdges: FlowLayoutEdge[] = edges
    .map((e) => ({ from: byId.get(e.from), to: byId.get(e.to) }))
    .filter((e): e is FlowLayoutEdge => e.from != null && e.to != null);

  return { nodes: laidOutNodes, edges: laidOutEdges, width, height };
}

export const FLOW_NODE_W = FLOW_COL_W;
export const FLOW_NODE_H = FLOW_ROW_H;
