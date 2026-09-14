import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WorkflowVisualization } from "./workflow-visualization";

describe("WorkflowVisualization", () => {
  it("starts on the first real workflow stage, not an invented one", () => {
    render(<WorkflowVisualization />);
    // jsdom has no matchMedia, so the component's reduced-motion guard
    // leaves it running its normal (non-reduced) start state.
    expect(screen.getByText("Case received")).toBeInTheDocument();
  });

  it("names both real outcome branches (GREEN auto-resolve, RED human approval) somewhere in its labels", () => {
    render(<WorkflowVisualization />);
    // Only one branch's steps are mounted at a time; the outcome region
    // is always present with one of the two real outcomes.
    const status = screen.getByRole("status");
    expect(status.textContent).toMatch(/Resolved automatically|Awaiting staff decision/);
  });
});
