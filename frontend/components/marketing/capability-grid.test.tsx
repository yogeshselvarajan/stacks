import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CapabilityGrid } from "./capability-grid";

describe("CapabilityGrid", () => {
  it("renders all six real architecture components, not invented ones", () => {
    render(<CapabilityGrid />);
    expect(screen.getByText("Stacks Agent")).toBeInTheDocument();
    expect(screen.getByText("ILL Disambiguation Specialist")).toBeInTheDocument();
    expect(screen.getByText("Overdue Escalation Sequencer")).toBeInTheDocument();
    expect(screen.getByText("Bedrock Guardrails")).toBeInTheDocument();
    expect(screen.getByText("AgentCore Memory")).toBeInTheDocument();
    expect(screen.getByText("HITL Approval Gate")).toBeInTheDocument();
  });

  it("labels the HITL gate as a deterministic decision, never claiming a fake AWS service for it", () => {
    render(<CapabilityGrid />);
    expect(screen.getByText("Deterministic, not a model decision")).toBeInTheDocument();
  });

  it("is anchorable from the nav via #capabilities", () => {
    const { container } = render(<CapabilityGrid />);
    expect(container.querySelector("#capabilities")).not.toBeNull();
  });
});
