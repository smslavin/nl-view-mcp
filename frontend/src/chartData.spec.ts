import { describe, expect, it } from "vitest";
import { layoutFlow, toChartJsData, toStatValue } from "./chartData";
import { barSpecFixture, flowSpecFixture, lineSpecFixture, statSpecFixture } from "./testFixtures";

describe("toChartJsData", () => {
  it("formats line-chart x values (Unix seconds) as UTC clock times", () => {
    const data = toChartJsData(lineSpecFixture);

    expect(data.labels).toEqual(["12:16 AM", "12:17 AM"]);
  });

  it("builds one dataset per series, sharing labels from the first series' x values", () => {
    const data = toChartJsData(lineSpecFixture);

    expect(data.datasets).toHaveLength(2);
    expect(data.datasets[0].label).toBe("North Tank Level (%)");
    expect(data.datasets[0].data).toEqual([51.2, 52.8]);
    expect(data.datasets[1].label).toBe("South Tank Level (%)");
  });

  it("handles categorical (bar) x values the same way as numeric ones", () => {
    const data = toChartJsData(barSpecFixture);

    expect(data.labels).toEqual(["north", "south"]);
    expect(data.datasets[0].data).toEqual([3.2, 1.1]);
  });

  it("assigns distinct colors per series", () => {
    const data = toChartJsData(lineSpecFixture);
    expect(data.datasets[0].borderColor).not.toBe(data.datasets[1].borderColor);
  });
});

describe("toStatValue", () => {
  it("extracts the single value and unit from a stat spec", () => {
    expect(toStatValue(statSpecFixture)).toEqual({ value: 74.77, unit: "gpm" });
  });
});

describe("layoutFlow", () => {
  it("lays out a straight chain one node per layer, left to right", () => {
    const layout = layoutFlow({
      ...flowSpecFixture,
      nodes: flowSpecFixture.nodes!.slice(0, 3),
      edges: flowSpecFixture.edges!.slice(0, 2),
    });

    const layerById = Object.fromEntries(layout.nodes.map((n) => [n.id, n.layer]));
    expect(layerById["west.tank_level"]).toBe(0);
    expect(layerById["west.pump_run_state"]).toBe(1);
    expect(layerById["west.flow_rate"]).toBe(2);
    // x strictly increases layer over layer -- reads left to right.
    const xs = layout.nodes.map((n) => n.x).sort((a, b) => a - b);
    expect(new Set(xs).size).toBe(3);
  });

  it("puts both children of a real branch in the same next layer, stacked", () => {
    const layout = layoutFlow(flowSpecFixture);

    const flowNode = layout.nodes.find((n) => n.id === "west.flow_rate")!;
    const flowBNode = layout.nodes.find((n) => n.id === "west.flow_rate_b")!;
    expect(flowNode.layer).toBe(2);
    expect(flowBNode.layer).toBe(2);
    expect(flowNode.x).toBe(flowBNode.x); // same layer -> same column
    expect(flowNode.y).not.toBe(flowBNode.y); // stacked, not overlapping
  });

  it("resolves edge endpoints to the same node objects the layout placed", () => {
    const layout = layoutFlow(flowSpecFixture);
    for (const edge of layout.edges) {
      expect(layout.nodes).toContain(edge.from);
      expect(layout.nodes).toContain(edge.to);
    }
  });

  it("returns an empty layout for a spec with no nodes", () => {
    expect(layoutFlow({ ...flowSpecFixture, nodes: [], edges: [] })).toEqual({
      nodes: [], edges: [], width: 0, height: 0,
    });
  });
});
