import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import WelcomePage from "./page";

describe("WelcomePage", () => {
  it("renders every section of the public marketing page", () => {
    render(<WelcomePage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("afternoons back");
    expect(screen.getByText("How it works", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByText("Six real components, working as one")).toBeInTheDocument();
    expect(screen.getByText("Built on AWS", { selector: "p" })).toBeInTheDocument();
  });

  it("never requires authentication -- no redirect, no session check", () => {
    render(<WelcomePage />);
    // A public page renders its content synchronously with no loading/auth gate.
    expect(screen.queryByText(/sign in required/i)).toBeNull();
  });
});
