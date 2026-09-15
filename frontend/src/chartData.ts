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
  const labels = spec.series[0]?.points.map((p) => formatLabel(p.x, spec.chart_type)) ?? [];

  return {
    labels,
    datasets: spec.series.map((series, i) => {
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
  const point = spec.series[0]?.points[0];
  return { value: point?.y ?? null, unit: spec.series[0]?.unit ?? "" };
}
