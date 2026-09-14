import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LiveDot } from "./live-dot";

describe("LiveDot", () => {
  it("renders as decorative (aria-hidden), never announced as content on its own", () => {
    const { container } = render(<LiveDot />);
    expect(container.firstChild).toHaveAttribute("aria-hidden", "true");
  });
});
