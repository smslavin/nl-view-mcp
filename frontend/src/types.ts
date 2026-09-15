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

export interface WidgetSpec {
  widget_type: "chart" | "stat";
  title: string;
  chart_type: "line" | "bar" | "stat";
  series: WidgetSeries[];
  size_hint: SizeHint;
}

export interface BoardWidget {
  id: string;
  instruction: string;
  spec: WidgetSpec;
}
