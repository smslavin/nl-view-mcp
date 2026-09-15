import type { WidgetSpec } from "./types";

export const lineSpecFixture: WidgetSpec = {
  widget_type: "chart",
  title: "Tank Level — Last 1 Hour",
  chart_type: "line",
  series: [
    {
      name: "North Tank Level",
      unit: "%",
      points: [
        { x: 1000, y: 51.2 },
        { x: 1060, y: 52.8 },
      ],
    },
    {
      name: "South Tank Level",
      unit: "%",
      points: [
        { x: 1000, y: 60.1 },
        { x: 1060, y: 59.4 },
      ],
    },
  ],
  size_hint: { w: 6, h: 4 },
};

export const barSpecFixture: WidgetSpec = {
  widget_type: "chart",
  title: "Pump Run Hours by Zone",
  chart_type: "bar",
  series: [
    {
      name: "Pump Run Hours",
      unit: "hours",
      points: [
        { x: "north", y: 3.2 },
        { x: "south", y: 1.1 },
      ],
    },
  ],
  size_hint: { w: 6, h: 4 },
};

export const statSpecFixture: WidgetSpec = {
  widget_type: "stat",
  title: "Current Flow Rate",
  chart_type: "stat",
  series: [
    {
      name: "Flow Rate",
      unit: "gpm",
      points: [{ x: "now", y: 74.77 }],
    },
  ],
  size_hint: { w: 3, h: 2 },
};

export const tableSpecFixture: WidgetSpec = {
  widget_type: "table",
  title: "Shift History",
  chart_type: "table",
  columns: [
    { key: "line", label: "Line", kind: "text" },
    { key: "id", label: "Shift ID", kind: "code" },
  ],
  rows: [
    { line: "Line 1", id: "line-1-current" },
    { line: "Line 2", id: "line-2-current" },
  ],
  size_hint: { w: 8, h: 4 },
};

// A straight chain (west.tank -> west.pump -> west.flow) plus the divergent
// zone's second edge (west.pump -> west.flow_b), so one fixture exercises
// both the uniform-chain and the real-branch layout case.
export const flowSpecFixture: WidgetSpec = {
  widget_type: "flow",
  title: "Flow Topology — West",
  chart_type: "flow",
  nodes: [
    { id: "west.tank_level", label: "West Tank Level" },
    { id: "west.pump_run_state", label: "West Pump Run State" },
    { id: "west.flow_rate", label: "West Flow Rate" },
    { id: "west.flow_rate_b", label: "West Auxiliary Flow Rate" },
  ],
  edges: [
    { from: "west.tank_level", to: "west.pump_run_state" },
    { from: "west.pump_run_state", to: "west.flow_rate" },
    { from: "west.pump_run_state", to: "west.flow_rate_b" },
  ],
  size_hint: { w: 6, h: 4 },
};
