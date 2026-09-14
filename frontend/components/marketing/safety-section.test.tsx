import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SafetySection } from "./safety-section";

describe("SafetySection", () => {
  it("states plainly that the model does not choose its own tier", () => {
    render(<SafetySection />);
    expect(screen.getByText(/doesn't choose its own safety tier/)).toBeInTheDocument();
  });

  it("shows all three real tiers via the shared TierBadge component", () => {
    render(<SafetySection />);
    expect(screen.getAllByRole("status")).toHaveLength(3);
  });

  it("is anchorable from the nav via #safety", () => {
    const { container } = render(<SafetySection />);
    expect(container.querySelector("#safety")).not.toBeNull();
  });
});
