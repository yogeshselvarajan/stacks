import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RowSkeleton, CardSkeleton } from "./skeletons";

describe("RowSkeleton", () => {
  it("renders exactly the requested number of column placeholders", () => {
    const { container } = render(
      <table>
        <tbody>
          <RowSkeleton columns={3} />
        </tbody>
      </table>
    );
    const cells = container.querySelectorAll("[data-testid='skeleton-cell']");
    expect(cells.length).toBe(3);
  });

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
  it("renders with at least 2 lines and an actions block", () => {
    const { container } = render(<CardSkeleton />);
    const lines = container.querySelectorAll("[data-testid='skeleton-line']");
    const actions = container.querySelector("[data-testid='skeleton-actions']");
    expect(lines.length).toBeGreaterThanOrEqual(2);
    expect(actions).toBeTruthy();
  });

  it("fills its lines and action blocks with the surface-2 token, not the border token", () => {
    const { container } = render(<CardSkeleton />);
    const line = container.querySelector("[data-testid='skeleton-line']") as HTMLElement;
    expect(line.style.background).toBe("var(--color-surface-2)");
  });
});
