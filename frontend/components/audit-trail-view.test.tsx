import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AuditTrailView } from "./audit-trail-view";
import { AUDIT_FIXTURE } from "@/lib/fixtures";

describe("AuditTrailView", () => {
  it("loading state: renders row skeletons in a table shape", () => {
    const { container } = render(<AuditTrailView entries={[]} status="loading" mode="list" />);
    expect(container.querySelector("[data-testid='skeleton-cell']")).not.toBeNull();
  });

  it("populated state: each row shows the tool name, tier badge, and actor, with tabular numerals on the sequence column", () => {
    render(<AuditTrailView entries={AUDIT_FIXTURE} status="ready" mode="list" />);
    expect(screen.getByText("resolve_room_conflict")).toBeInTheDocument();
    const sequenceCell = screen.getByText("1");
    expect(sequenceCell).toHaveStyle({ fontVariantNumeric: "tabular-nums" });
  });

  it("empty state: names the filter as the reason nothing matches, not a bare 'no data'", () => {
    render(<AuditTrailView entries={[]} status="ready" mode="list" />);
    expect(screen.getByText(/no audit entries match/i)).toBeInTheDocument();
  });

  it("error state: a specific, retry-oriented message", () => {
    render(<AuditTrailView entries={[]} status="error" mode="list" />);
    expect(screen.getByText(/failed to load the audit trail/i)).toBeInTheDocument();
  });

  it("trace mode: renders entries as a chronological, timestamp-ordered timeline", () => {
    render(<AuditTrailView entries={AUDIT_FIXTURE} status="ready" mode="trace" />);
    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("resolve_room_conflict");
    expect(items[1]).toHaveTextContent("notify_parties");
  });

  it("the trace-mode loading skeleton lines use the surface-2 fill token, not the border token", () => {
    const { container } = render(<AuditTrailView entries={[]} status="loading" mode="trace" />);
    const line = container.querySelector("[data-testid='skeleton-line']") as HTMLElement;
    expect(line.style.background).toBe("var(--color-surface-2)");
  });
});
