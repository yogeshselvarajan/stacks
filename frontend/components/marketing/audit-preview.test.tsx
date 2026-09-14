import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AuditPreview } from "./audit-preview";

describe("AuditPreview", () => {
  it("labels itself illustrative, never implying this is a live production feed", () => {
    render(<AuditPreview />);
    expect(screen.getByText(/Illustrative sequence/)).toBeInTheDocument();
  });

  it("shows the real audit stages a case actually produces", () => {
    render(<AuditPreview />);
    expect(screen.getByText("Case received")).toBeInTheDocument();
    expect(screen.getByText("Route committed")).toBeInTheDocument();
  });
});
