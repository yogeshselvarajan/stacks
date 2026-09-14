import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProblemSection } from "./problem-section";

describe("ProblemSection", () => {
  it("names the real, cited statistic rather than an invented one", () => {
    render(<ProblemSection />);
    expect(screen.getByText(/OCLC's own Penn State member story/)).toBeInTheDocument();
  });

  it("states the exception-queue thesis", () => {
    render(<ProblemSection />);
    expect(screen.getByText("Every library system has an exception queue.")).toBeInTheDocument();
  });
});
