import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WorkflowsSection } from "./workflows-section";

describe("WorkflowsSection", () => {
  it("lists all three real workflows collapsed by default", () => {
    render(<WorkflowsSection />);
    expect(screen.getByText("Room booking")).toBeInTheDocument();
    expect(screen.getByText("Interlibrary loan")).toBeInTheDocument();
    expect(screen.getByText("Overdue escalation")).toBeInTheDocument();
    expect(screen.queryByText(/Stacks reads the library's own priority policy/)).toBeNull();
  });

  it("expands a workflow's detail and safety tier on click", () => {
    render(<WorkflowsSection />);
    fireEvent.click(screen.getByRole("button", { name: /room booking/i }));
    expect(screen.getByText(/Stacks reads the library's own priority policy/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /room booking/i })).toHaveAttribute("aria-expanded", "true");
  });

  it("collapses a previously expanded workflow when clicked again", () => {
    render(<WorkflowsSection />);
    const button = screen.getByRole("button", { name: /room booking/i });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "false");
  });
});
