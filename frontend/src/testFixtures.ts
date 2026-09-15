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
