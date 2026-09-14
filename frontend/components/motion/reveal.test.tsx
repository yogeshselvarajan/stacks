import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Reveal } from "./reveal";

describe("Reveal", () => {
  it("renders its children immediately (content is never blocked on the observer)", () => {
    render(
      <Reveal>
        <p>Hello</p>
      </Reveal>,
    );
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });
});
