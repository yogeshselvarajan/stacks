import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CtaSection } from "./cta-section";

describe("CtaSection", () => {
  it("links its call to action to /login", () => {
    render(<CtaSection />);
    expect(screen.getByRole("link", { name: /sign in/i })).toHaveAttribute("href", "/login");
  });
});
