// frontend/components/overdue-queue-view.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OverdueQueueView } from "./overdue-queue-view";
import { OVERDUE_QUEUE_FIXTURE } from "@/lib/fixtures";

describe("OverdueQueueView", () => {
  it("loading state: renders card skeletons", () => {
    const { container } = render(<OverdueQueueView cases={[]} status="loading" />);
    expect(container.querySelector("[data-testid='skeleton-actions']")).not.toBeNull();
  });

  it("populated state: renders a step-tracker, not a plain status string", () => {
    render(<OverdueQueueView cases={OVERDUE_QUEUE_FIXTURE} status="ready" />);
    expect(screen.getByText("Informational")).toBeInTheDocument();
    expect(screen.getByText("Fee mention")).toBeInTheDocument();
    expect(screen.getByText(/held for review/i)).toBeInTheDocument();
  });

  it("populated state: shows the item title and patron name, not just the raw circulation record id", () => {
    render(<OverdueQueueView cases={OVERDUE_QUEUE_FIXTURE} status="ready" />);
    expect(screen.getByText(/The Great Gatsby/)).toBeInTheDocument();
    expect(screen.getByText(/Maria Chen/)).toBeInTheDocument();
    expect(screen.getByText("circ_1")).toBeInTheDocument();
  });

  it("shows the Memory recall indicator distinctly from the step-tracker", () => {
    render(<OverdueQueueView cases={OVERDUE_QUEUE_FIXTURE} status="ready" />);
    expect(screen.getByText(/hardship flag on file/i)).toBeInTheDocument();
    expect(screen.getByTestId("memory-recall-indicator")).toBeInTheDocument();
  });

  it("empty state: a positive, specific message", () => {
    render(<OverdueQueueView cases={[]} status="ready" />);
    expect(screen.getByText(/no overdue cases right now/i)).toBeInTheDocument();
  });

  it("error state: a specific, retry-oriented message", () => {
    render(<OverdueQueueView cases={[]} status="error" />);
    expect(screen.getByText(/failed to load the overdue queue/i)).toBeInTheDocument();
  });

  it("shows a clear access-denied message when status is forbidden, not the generic failure message", () => {
    render(<OverdueQueueView cases={[]} status="forbidden" />);
    expect(screen.getByText("You do not have access to this workflow.")).toBeInTheDocument();
  });

  it("each tier-history step pill uses the surface-2 nested-fill token, not the canvas background token", () => {
    render(<OverdueQueueView cases={OVERDUE_QUEUE_FIXTURE} status="ready" />);
    // "Informational" renders inside a nested <span class="font-medium">; the
    // pill with the background style is that span's PARENT, not an ancestor
    // reachable via .closest("span") (which matches the inner span itself
    // before ever walking up).
    const stepPill = screen.getByText("Informational").parentElement;
    expect(stepPill?.style.background).toBe("var(--color-surface-2)");
  });
});
