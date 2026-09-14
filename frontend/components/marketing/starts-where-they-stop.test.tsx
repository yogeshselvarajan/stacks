import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StartsWhereTheyStop } from "./starts-where-they-stop";

describe("StartsWhereTheyStop", () => {
  it("shows the before flow ending at a human, not a resolution", () => {
    render(<StartsWhereTheyStop />);
    expect(screen.getByText("Without Stacks")).toBeInTheDocument();
    expect(screen.getByText("Staff")).toBeInTheDocument();
  });

  it("shows the with-Stacks flow ending at Resolution", () => {
    render(<StartsWhereTheyStop />);
    expect(screen.getByText("With Stacks")).toBeInTheDocument();
    expect(screen.getByText("Resolution")).toBeInTheDocument();
  });
});
