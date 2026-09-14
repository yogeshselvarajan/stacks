import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Hero } from "./hero";

describe("Hero", () => {
  it("states the real product value proposition, not vague AI marketing copy", () => {
    render(<Hero />);
    // Read via its accessible name, not raw textContent: the entrance
    // animation splits the heading into per-word spans for the reveal,
    // which can disturb inter-word spacing in the raw DOM text. The
    // heading's aria-label is set from the original sentence before that
    // split happens, specifically so the accessible name stays exact.
    expect(screen.getByRole("heading", { level: 1 })).toHaveAccessibleName(
      "Give library staff their afternoons back.",
    );
  });

  it("has a primary sign-in CTA linking to /login", () => {
    render(<Hero />);
    const signIn = screen.getAllByRole("link", { name: /sign in/i })[0];
    expect(signIn).toHaveAttribute("href", "/login");
  });

  it("has a secondary CTA that scrolls to the how-it-works section", () => {
    render(<Hero />);
    expect(screen.getByRole("link", { name: /see how it works/i })).toHaveAttribute("href", "#how-it-works");
  });
});
