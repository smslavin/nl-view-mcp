import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { flowSpecFixture } from "../testFixtures";
import FlowWidget from "./FlowWidget.vue";

describe("FlowWidget", () => {
  it("renders one node group per node and one edge path per edge", () => {
    const wrapper = mount(FlowWidget, { props: { spec: flowSpecFixture } });

    expect(wrapper.findAll("svg g")).toHaveLength(flowSpecFixture.nodes!.length);
    // svg > path: edges are direct children; the arrowhead marker's path
    // lives nested under defs/marker, three levels down, not a direct child.
    expect(wrapper.findAll("svg > path")).toHaveLength(flowSpecFixture.edges!.length);
  });

  it("renders the empty state when there are no nodes", () => {
    const wrapper = mount(FlowWidget, {
      props: { spec: { ...flowSpecFixture, nodes: [], edges: [] } },
    });

    expect(wrapper.text()).toContain("No routing data.");
    expect(wrapper.find("svg").exists()).toBe(false);
  });
});
