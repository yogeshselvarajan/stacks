import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TierBadge } from "./tier-badge";

describe("TierBadge", () => {
  it("renders GREEN with its icon, color, and label together", () => {
    render(<TierBadge tier="GREEN" />);
    const badge = screen.getByRole("status");
    expect(badge).toHaveTextContent("Auto-executed");
    expect(badge.querySelector("svg")).not.toBeNull();
  });

  it("renders YELLOW with its own label, never reusing GREEN's", () => {
    render(<TierBadge tier="YELLOW" />);
    expect(screen.getByRole("status")).toHaveTextContent("Awaiting confirmation");
  });

  it("renders RED with its own label", () => {
    render(<TierBadge tier="RED" />);
    expect(screen.getByRole("status")).toHaveTextContent("Requires review");
  });

  it("never renders color as the only signal (a text label is always present)", () => {
    render(<TierBadge tier="RED" />);
    // A colorblind user reading only text content must still identify the tier.
    expect(screen.getByRole("status").textContent).not.toBe("");
  });
});
