import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AppShell } from "./app-shell";

describe("AppShell", () => {
  it("shows the Approval Inbox nav item with a live count badge", () => {
    render(
      <AppShell role="branch_manager" pendingCounts={{ approvals: 3 }} activeRoute="/">
        <p>content</p>
      </AppShell>
    );
    const approvalsLink = screen.getByRole("link", { name: /approval inbox/i });
    expect(approvalsLink).toHaveTextContent("3");
  });

  it("hides the count badge entirely when there are zero pending approvals (not a badge showing 0)", () => {
    render(
      <AppShell role="branch_manager" pendingCounts={{ approvals: 0 }} activeRoute="/">
        <p>content</p>
      </AppShell>
    );
    const approvalsLink = screen.getByRole("link", { name: /approval inbox/i });
    expect(approvalsLink.querySelector("[data-testid='approvals-count']")).toBeNull();
  });

  it("renders every nav link with the shared focus-ring class", () => {
    render(
      <AppShell role="branch_manager" pendingCounts={{ approvals: 0 }} activeRoute="/">
        <p>content</p>
      </AppShell>
    );
    for (const link of screen.getAllByRole("link")) {
      expect(link.className).toContain("stacks-focus-ring");
    }
  });

  it("gives every nav link default, hover, focus, and active/pressed styling (not just default+hover)", () => {
    render(
      <AppShell role="branch_manager" pendingCounts={{ approvals: 0 }} activeRoute="/">
        <p>content</p>
      </AppShell>
    );
    for (const link of screen.getAllByRole("link")) {
      // Default state: explicit ink color and layout classes.
      expect(link.className).toContain("px-3");
      // Hover state.
      expect(link.className).toMatch(/hover:/);
      // Focus state: the shared custom focus ring (never the browser default).
      expect(link.className).toContain("stacks-focus-ring");
      // Active/pressed state.
      expect(link.className).toMatch(/active:/);
    }
  });

  it("marks the current route's nav link distinctly (active-route state) via aria-current", () => {
    render(
      <AppShell role="branch_manager" pendingCounts={{ approvals: 0 }} activeRoute="/calendar">
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
      <AppShell role="branch_manager" pendingCounts={{ approvals: 0 }} activeRoute="/">
        <p>unique content marker</p>
      </AppShell>
    );
    expect(screen.getByText("unique content marker")).toBeInTheDocument();
  });
});
