import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WelcomeNav } from "./welcome-nav";

describe("WelcomeNav", () => {
  it("renders the Stacks wordmark and a Sign in link to /login", () => {
    render(<WelcomeNav />);
    expect(screen.getByText("Stacks")).toBeInTheDocument();
    const signIn = screen.getByRole("link", { name: /sign in/i });
    expect(signIn).toHaveAttribute("href", "/login");
  });

  it("links to every on-page section by its anchor id", () => {
    render(<WelcomeNav />);
    expect(screen.getByRole("link", { name: /how it works/i })).toHaveAttribute("href", "#how-it-works");
    expect(screen.getByRole("link", { name: /capabilities/i })).toHaveAttribute("href", "#capabilities");
    expect(screen.getByRole("link", { name: /built on aws/i })).toHaveAttribute("href", "#built-on-aws");
  });
});
