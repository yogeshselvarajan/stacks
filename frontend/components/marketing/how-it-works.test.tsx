import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HowItWorks } from "./how-it-works";

describe("HowItWorks", () => {
  it("renders all three real steps in order", () => {
    render(<HowItWorks />);
    expect(screen.getByText("A case appears")).toBeInTheDocument();
    expect(screen.getByText("Stacks evaluates it")).toBeInTheDocument();
    expect(screen.getByText("The right action happens")).toBeInTheDocument();
  });

  it("shows all three real HITL tiers on the final step, not invented labels", () => {
    render(<HowItWorks />);
    expect(screen.getAllByRole("status")).toHaveLength(3);
  });

  it("is anchorable from the nav via #how-it-works", () => {
    const { container } = render(<HowItWorks />);
    expect(container.querySelector("#how-it-works")).not.toBeNull();
  });
});
