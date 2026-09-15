import { describe, expect, it } from "vitest";
import { statSpecFixture } from "../testFixtures";
import { useBoard } from "./useBoard";

describe("useBoard", () => {
  it("starts empty", () => {
    const { widgets } = useBoard();
    expect(widgets.value).toEqual([]);
  });

  it("accumulates widgets across successive calls instead of replacing them", () => {
    const { widgets, addWidget } = useBoard();

    addWidget("what's the current flow rate", statSpecFixture);
    addWidget("what's the current flow rate again", statSpecFixture);

    expect(widgets.value).toHaveLength(2);
    expect(widgets.value[0].instruction).toBe("what's the current flow rate");
  });

  it("assigns each widget a unique id", () => {
    const { widgets, addWidget } = useBoard();
    addWidget("a", statSpecFixture);
    addWidget("b", statSpecFixture);
    expect(widgets.value[0].id).not.toBe(widgets.value[1].id);
  });

  it("clear empties the board", () => {
    const { widgets, addWidget, clear } = useBoard();
    addWidget("a", statSpecFixture);
    clear();
    expect(widgets.value).toEqual([]);
  });

  it("is independent per call, not shared module-level state", () => {
    const boardA = useBoard();
    const boardB = useBoard();
    boardA.addWidget("a", statSpecFixture);
    expect(boardB.widgets.value).toEqual([]);
  });
});
