import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApprovalInboxView } from "./approval-inbox-view";
import { APPROVAL_CASES_FIXTURE, EMPTY_APPROVAL_CASES_FIXTURE } from "@/lib/fixtures";

describe("ApprovalInboxView", () => {
  it("loading state: renders card skeletons, not a spinner", () => {
    const { container } = render(<ApprovalInboxView cases={[]} status="loading" activeCaseId={null} resolvingCaseId={null} />);
    expect(container.querySelector("[data-testid='skeleton-line']")).not.toBeNull();
  });

  it("populated state: sorts RED cases before YELLOW", () => {
    render(<ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" activeCaseId={null} resolvingCaseId={null} />);
    const rows = screen.getAllByTestId("approval-row");
    expect(rows[0]).toHaveTextContent(/Room 204/);
  });

  it("empty state: a caught-up queue is framed positively, not as a generic 'no data' stub", () => {
    render(<ApprovalInboxView cases={EMPTY_APPROVAL_CASES_FIXTURE} status="ready" activeCaseId={null} resolvingCaseId={null} />);
    expect(screen.getByText(/queue is caught up/i)).toBeInTheDocument();
  });

  it("error state: shows a specific, retry-oriented message", () => {
    render(<ApprovalInboxView cases={[]} status="error" activeCaseId={null} resolvingCaseId={null} />);
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
  });

  it("each row links to its case detail route", () => {
    render(<ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" activeCaseId={null} resolvingCaseId={null} />);
    const rows = screen.getAllByTestId("approval-row");
    expect(rows[0]).toHaveAttribute("href", `/approvals/${encodeURIComponent(APPROVAL_CASES_FIXTURE[0].caseId)}`);
  });

  it("highlights the active (selected) case row distinctly", () => {
    render(
      <ApprovalInboxView
        cases={APPROVAL_CASES_FIXTURE}
        status="ready"
        activeCaseId={APPROVAL_CASES_FIXTURE[1].caseId}
        resolvingCaseId={null}
      />
    );
    const rows = screen.getAllByTestId("approval-row");
    const activeRow = rows.find((r) => r.getAttribute("href") === `/approvals/${encodeURIComponent(APPROVAL_CASES_FIXTURE[1].caseId)}`);
    expect(activeRow?.style.background).toBe("var(--color-surface-2)");
  });

  it("marks the resolving case's row with the collapse-out class", () => {
    render(
      <ApprovalInboxView
        cases={APPROVAL_CASES_FIXTURE}
        status="ready"
        activeCaseId={null}
        resolvingCaseId={APPROVAL_CASES_FIXTURE[0].caseId}
      />
    );
    const rows = screen.getAllByTestId("approval-row");
    const resolvingRow = rows.find((r) => r.getAttribute("href") === `/approvals/${encodeURIComponent(APPROVAL_CASES_FIXTURE[0].caseId)}`);
    expect(resolvingRow?.className).toContain("approval-row-collapsing");
  });

  it("every row carries the shared focus-ring class and hover/active styling", () => {
    render(<ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" activeCaseId={null} resolvingCaseId={null} />);
    for (const row of screen.getAllByTestId("approval-row")) {
      expect(row.className).toContain("stacks-focus-ring");
      expect(row.className).toMatch(/hover:/);
      expect(row.className).toMatch(/active:/);
    }
  });

  it("each row shows a tier-colored dot indicator, not a full TierBadge (kept compact for scanning)", () => {
    render(<ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" activeCaseId={null} resolvingCaseId={null} />);
    const rows = screen.getAllByTestId("approval-row");
    expect(rows[0].querySelector("[data-testid='tier-dot']")).not.toBeNull();
  });
});
