import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { tableSpecFixture } from "../testFixtures";
import TableWidget from "./TableWidget.vue";

describe("TableWidget", () => {
  it("renders one header cell per column and one row per record", () => {
    const wrapper = mount(TableWidget, { props: { spec: tableSpecFixture } });

    const headers = wrapper.findAll("th").map((th) => th.text());
    expect(headers).toEqual(["Line", "Shift ID"]);

    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(2);
    expect(rows[0]!.text()).toContain("Line 1");
    expect(rows[0]!.text()).toContain("line-1-current");
  });

  it("renders the empty state when there are no rows", () => {
    const wrapper = mount(TableWidget, {
      props: { spec: { ...tableSpecFixture, rows: [] } },
    });

    expect(wrapper.text()).toContain("No rows.");
    expect(wrapper.findAll("tbody tr")).toHaveLength(0);
  });

  it("renders a missing cell value as an em dash, not blank", () => {
    const wrapper = mount(TableWidget, {
      props: { spec: { ...tableSpecFixture, rows: [{ line: "Line 3", id: null }] } },
    });

    expect(wrapper.get("tbody tr").text()).toContain("—");
  });
});
