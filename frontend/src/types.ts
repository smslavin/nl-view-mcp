export interface WidgetPoint {
  x: number | string;
  y: number | null;
}

export interface WidgetSeries {
  name: string;
  unit: string;
  points: WidgetPoint[];
}

export interface SizeHint {
  w: number;
  h: number;
}

// A column's `kind` is the renderer's styling cue, not a type system --
// "code" gets monospace + truncate + full-value-on-hover (a lot code, a
// node id), "number" gets right-aligned tabular figures, "text" is plain.
export interface TableColumn {
  key: string;
  label: string;
  kind: "text" | "number" | "code";
}

export type TableRow = Record<string, string | number | null>;

export interface FlowNode {
  id: string;
  label: string;
}

export interface FlowEdge {
  from: string;
  to: string;
}

// One flat interface for every chart_type, same low-ceremony shape the
// Python side returns (a dict with the keys that chart_type needs) rather
// than a discriminated union -- only the fields a given chart_type reads
// are ever populated. series is used by line/bar/stat; columns+rows by
// table; nodes+edges by flow.
export interface WidgetSpec {
  widget_type: "chart" | "stat" | "table" | "flow";
  title: string;
  chart_type: "line" | "bar" | "stat" | "table" | "flow";
  series?: WidgetSeries[];
  columns?: TableColumn[];
  rows?: TableRow[];
  nodes?: FlowNode[];
  edges?: FlowEdge[];
  size_hint: SizeHint;
}

export interface BoardWidget {
  id: string;
  instruction: string;
  spec: WidgetSpec;
}
