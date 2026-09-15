import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { statSpecFixture } from "../testFixtures";
import StatWidget from "./StatWidget.vue";

describe("StatWidget", () => {
  it("renders the value and unit from the spec", () => {
    const wrapper = mount(StatWidget, { props: { spec: statSpecFixture } });

    expect(wrapper.text()).toContain("74.77");
    expect(wrapper.text()).toContain("gpm");
  });

  it("renders an em dash when the value is null", () => {
    const spec = {
      ...statSpecFixture,
      series: [{ ...statSpecFixture.series![0], points: [{ x: "now", y: null }] }],
    };
    const wrapper = mount(StatWidget, { props: { spec } });

    expect(wrapper.text()).toContain("—");
  });
});
