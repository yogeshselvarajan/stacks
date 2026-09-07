import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RowSkeleton, CardSkeleton } from "./skeletons";

describe("RowSkeleton", () => {
  it("fills each cell's pulsing block with the surface-2 token, not the border token", () => {
    const { container } = render(
      <table>
        <tbody>
          <RowSkeleton columns={3} />
        </tbody>
      </table>
    );
    const cell = container.querySelector("[data-testid='skeleton-cell']") as HTMLElement;
    expect(cell.style.background).toBe("var(--color-surface-2)");
  });
});

describe("CardSkeleton", () => {
  it("fills its lines and action blocks with the surface-2 token, not the border token", () => {
    const { container } = render(<CardSkeleton />);
    const line = container.querySelector("[data-testid='skeleton-line']") as HTMLElement;
    expect(line.style.background).toBe("var(--color-surface-2)");
  });
});
