import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ActionVsAnswer } from "./action-vs-answer";

describe("ActionVsAnswer", () => {
  it("names the real library chatbots by name, not a generic strawman", () => {
    render(<ActionVsAnswer />);
    expect(screen.getByText(/USF LINK/)).toBeInTheDocument();
    expect(screen.getByText(/SJSU KingbotGPT/)).toBeInTheDocument();
  });

  it("contrasts question-to-answer against case-to-outcome", () => {
    render(<ActionVsAnswer />);
    expect(screen.getByText("Question")).toBeInTheDocument();
    expect(screen.getByText("Outcome")).toBeInTheDocument();
  });
});
