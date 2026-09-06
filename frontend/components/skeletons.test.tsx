import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RowSkeleton, CardSkeleton } from "./skeletons";

describe("skeleton primitives", () => {
  it("RowSkeleton renders exactly the requested number of column placeholders", () => {
    const { container } = render(<RowSkeleton columns={4} />);
    expect(container.querySelectorAll("[data-testid='skeleton-cell']").length).toBe(4);
  });

  it("CardSkeleton renders a shape matching a case card (title line, meta line, action row)", () => {
    const { container } = render(<CardSkeleton />);
    expect(container.querySelectorAll("[data-testid='skeleton-line']").length).toBeGreaterThanOrEqual(2);
    expect(container.querySelector("[data-testid='skeleton-actions']")).not.toBeNull();
  });
});
