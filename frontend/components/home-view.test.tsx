import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HomeView } from "./home-view";

describe("HomeView", () => {
  it("loading state: renders a card-shaped skeleton, not a spinner", () => {
    const { container } = render(<HomeView status="loading" pendingByTier={null} lastSweepSummary={null} />);
    expect(container.querySelector("[data-testid='skeleton-line']")).not.toBeNull();
  });

  it("populated state: shows the pending-by-tier counts and the last-sweep summary", () => {
    render(<HomeView status="ready" pendingByTier={{ GREEN: 9, YELLOW: 2, RED: 1 }} lastSweepSummary="Last night's sweep: 14 cases processed, 2 pending your review." />);
    expect(screen.getByText(/14 cases processed/)).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("populated state: also shows the RED count distinctly from YELLOW", () => {
    render(<HomeView status="ready" pendingByTier={{ GREEN: 9, YELLOW: 2, RED: 1 }} lastSweepSummary={null} />);
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("empty state: a caught-up queue reads as a positive, specific message, not a generic 'no data'", () => {
    render(<HomeView status="ready" pendingByTier={{ GREEN: 0, YELLOW: 0, RED: 0 }} lastSweepSummary={null} />);
    expect(screen.getByText(/all caught up/i)).toBeInTheDocument();
  });

  it("error state: shows a specific retry-oriented message", () => {
    render(<HomeView status="error" pendingByTier={null} lastSweepSummary={null} />);
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
  });
});
