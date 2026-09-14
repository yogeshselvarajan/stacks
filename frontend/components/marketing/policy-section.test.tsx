import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PolicySection } from "./policy-section";

describe("PolicySection", () => {
  it("shows a real cited clause id, matching the console's own approval screen", () => {
    render(<PolicySection />);
    expect(screen.getByText("RBP-1")).toBeInTheDocument();
  });

  it("states the citation-not-invention differentiator", () => {
    render(<PolicySection />);
    expect(screen.getByText(/doesn't invent the rule/)).toBeInTheDocument();
  });
});
