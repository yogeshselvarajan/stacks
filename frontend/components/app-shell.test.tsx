import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AppShell } from "./app-shell";

describe("AppShell", () => {
  it("shows the Approval Inbox nav item with a live count badge", () => {
    render(
      <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 3 }} activeRoute="/" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    const approvalsLink = screen.getByRole("link", { name: /approval inbox/i });
    expect(approvalsLink).toHaveTextContent("3");
  });

  it("hides the count badge entirely when there are zero pending approvals (not a badge showing 0)", () => {
    render(
      <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    const approvalsLink = screen.getByRole("link", { name: /approval inbox/i });
    expect(approvalsLink.querySelector("[data-testid='approvals-count']")).toBeNull();
  });

  it("renders every nav link with the shared focus-ring class", () => {
    render(
      <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    for (const link of screen.getAllByRole("link")) {
      expect(link.className).toContain("stacks-focus-ring");
    }
  });

  it("gives every nav link default, hover, focus, and active/pressed styling (not just default+hover)", () => {
    render(
      <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    for (const link of screen.getAllByRole("link")) {
      expect(link.className).toContain("px-3");
      expect(link.className).toMatch(/hover:/);
      expect(link.className).toContain("stacks-focus-ring");
      expect(link.className).toMatch(/active:/);
    }
  });

  it("marks the current route's nav link distinctly (active-route state) via aria-current", () => {
    render(
      <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/calendar" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    const calendarLink = screen.getByRole("link", { name: /calendar/i });
    expect(calendarLink).toHaveAttribute("aria-current", "page");
    const approvalsLink = screen.getByRole("link", { name: /approval inbox/i });
    expect(approvalsLink).not.toHaveAttribute("aria-current");
  });

  it("renders the passed children inside the main content area", () => {
    render(
      <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole={null}>
        <p>unique content marker</p>
      </AppShell>
    );
    expect(screen.getByText("unique content marker")).toBeInTheDocument();
  });

  it("shows the tenant name pinned above the nav groups", () => {
    render(
      <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    expect(screen.getByText("Central Branch")).toBeInTheDocument();
  });

  it("groups the nav into Workflows and Records sections, each with a visible group label", () => {
    render(
      <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    expect(screen.getByText("Workflows")).toBeInTheDocument();
    expect(screen.getByText("Records")).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: /primary/i });
    const workflowsGroup = screen.getByText("Workflows").closest("div");
    // Approval Inbox, Calendar, ILL Queue, and Overdue Queue all belong to
    // the Workflows group; Audit Trail belongs to Records, not Workflows.
    expect(workflowsGroup?.textContent).toContain("Approval Inbox");
    expect(workflowsGroup?.textContent).toContain("Overdue Queue");
    expect(workflowsGroup?.textContent).not.toContain("Audit Trail");
    expect(nav.textContent).toContain("Audit Trail");
  });

  it("the active nav item gets a distinct background, not just plain-text emphasis", () => {
    render(
      <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/calendar" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    const calendarLink = screen.getByRole("link", { name: /calendar/i });
    expect(calendarLink.style.background).toBe("var(--color-surface-2)");
    const approvalsLink = screen.getByRole("link", { name: /approval inbox/i });
    expect(approvalsLink.style.background).toBe("transparent");
  });

  it("shows a real, honest provenance line linking to the hackathon, not a fake status", () => {
    render(
      <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    expect(screen.getByText("Operational")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /agents for humans/i })).toHaveAttribute(
      "href",
      "https://agentsforhumans.devpost.com/",
    );
  });

  it("hides Calendar-irrelevant workflow items for room_booking_staff, keeps Calendar, Home, and Audit", () => {
    render(
      <AppShell role="room_booking_staff" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    expect(screen.getByRole("link", { name: /calendar/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /ill queue/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /overdue queue/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /approval inbox/i })).toBeNull();
    expect(screen.getByRole("link", { name: /home/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /audit trail/i })).toBeInTheDocument();
  });

  it("shows Approval Inbox for a role with case_review_role set, even if the base role would not normally see it", () => {
    render(
      <AppShell role="circulation_staff" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole="librarian_case_review">
        <p>content</p>
      </AppShell>
    );
    expect(screen.getByRole("link", { name: /approval inbox/i })).toBeInTheDocument();
  });

  it("shows every nav item for branch_manager regardless of caseReviewRole", () => {
    render(
      <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    expect(screen.getByRole("link", { name: /calendar/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ill queue/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /overdue queue/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /approval inbox/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /audit trail/i })).toBeInTheDocument();
  });

  it("shows ILL Queue only for ill_coordinator and branch_manager", () => {
    render(
      <AppShell role="ill_coordinator" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    expect(screen.getByRole("link", { name: /ill queue/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /calendar/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /overdue queue/i })).toBeNull();
  });

  it("shows Overdue Queue only for circulation_staff and branch_manager", () => {
    render(
      <AppShell role="circulation_staff" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/" caseReviewRole={null}>
        <p>content</p>
      </AppShell>
    );
    expect(screen.getByRole("link", { name: /overdue queue/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /calendar/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /ill queue/i })).toBeNull();
  });
});
