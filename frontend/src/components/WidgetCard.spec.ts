import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { barSpecFixture, lineSpecFixture, statSpecFixture } from "../testFixtures";
import BarWidget from "./BarWidget.vue";
import LineWidget from "./LineWidget.vue";
import StatWidget from "./StatWidget.vue";
import WidgetCard from "./WidgetCard.vue";

// shallowMount: LineWidget/BarWidget render real Chart.js canvases, which
// jsdom can't back. Dispatch and layout are what this component owns --
// chart rendering itself is chartData.spec.ts's job.
function mountCard(spec: typeof lineSpecFixture) {
  return shallowMount(WidgetCard, {
    props: { widget: { id: "w1", instruction: "test", spec } },
  });
}

describe("WidgetCard", () => {
  it("renders the widget title", () => {
    const wrapper = mountCard(lineSpecFixture);
    expect(wrapper.get("h3").text()).toBe("Tank Level — Last 1 Hour");
  });

  it.each([
    ["line", lineSpecFixture, LineWidget],
    ["bar", barSpecFixture, BarWidget],
    ["stat", statSpecFixture, StatWidget],
  ] as const)("dispatches chart_type %s to the matching component", (_label, spec, expected) => {
    const wrapper = mountCard(spec);
    expect(wrapper.findComponent(expected).exists()).toBe(true);
  });

  it("sizes the grid column span from size_hint.w", () => {
    const wrapper = mountCard(lineSpecFixture);
    expect(wrapper.attributes("style")).toContain("grid-column: span 6");
  });

  it("clamps an oversized size_hint.w to the 12-column grid", () => {
    const spec = { ...lineSpecFixture, size_hint: { w: 20, h: 4 } };
    const wrapper = mountCard(spec);
    expect(wrapper.attributes("style")).toContain("grid-column: span 12");
  });
});
