import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Hero } from "./hero";

describe("Hero", () => {
  it("states the real product value proposition, not vague AI marketing copy", () => {
    render(<Hero />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
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
