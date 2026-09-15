import { describe, expect, it } from "vitest";
import { toChartJsData, toStatValue } from "./chartData";
import { barSpecFixture, lineSpecFixture, statSpecFixture } from "./testFixtures";

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
