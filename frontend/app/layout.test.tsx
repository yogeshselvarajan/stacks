import { describe, expect, it } from "vitest";

describe("scaffolding smoke test", () => {
  it("vitest and jsdom are wired correctly", () => {
    document.body.innerHTML = "<p>ok</p>";
    expect(document.body.textContent).toBe("ok");
  });
});
