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
});
