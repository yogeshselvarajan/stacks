import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApprovalInboxView } from "./approval-inbox-view";
import { APPROVAL_CASES_FIXTURE, EMPTY_APPROVAL_CASES_FIXTURE } from "@/lib/fixtures";

describe("ApprovalInboxView", () => {
  it("loading state: renders card skeletons, not a spinner", () => {
    const { container } = render(<ApprovalInboxView cases={[]} status="loading" onResolve={vi.fn()} resolvingCaseId={null} />);
    expect(container.querySelector("[data-testid='skeleton-actions']")).not.toBeNull();
  });

  it("populated state: sorts RED cases before YELLOW", () => {
    render(<ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" onResolve={vi.fn()} resolvingCaseId={null} />);
    const statuses = screen.getAllByRole("status").map((el) => el.textContent);
    expect(statuses[0]).toContain("Requires review");
  });

  it("empty state: a caught-up queue is framed positively, not as a generic 'no data' stub", () => {
    render(<ApprovalInboxView cases={EMPTY_APPROVAL_CASES_FIXTURE} status="ready" onResolve={vi.fn()} resolvingCaseId={null} />);
    expect(screen.getByText(/queue is caught up/i)).toBeInTheDocument();
  });

  it("error state: shows a specific, retry-oriented message", () => {
    render(<ApprovalInboxView cases={[]} status="error" onResolve={vi.fn()} resolvingCaseId={null} />);
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
  });

  it("RED cards never render a trust-mode toggle", () => {
    render(<ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" onResolve={vi.fn()} resolvingCaseId={null} />);
    const redCard = screen.getByText(/Room 204/).closest("[data-testid='approval-card']");
    expect(redCard?.querySelector("[data-testid='trust-mode-toggle']")).toBeNull();
  });

  it("YELLOW cards render a trust-mode toggle", () => {
    render(<ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" onResolve={vi.fn()} resolvingCaseId={null} />);
    const yellowCard = screen.getByText(/Left Hand of Darkness/).closest("[data-testid='approval-card']");
    expect(yellowCard?.querySelector("[data-testid='trust-mode-toggle']")).not.toBeNull();
  });

  it("the resolving case shows a loading button state, and its card carries the signature resolve transition class", () => {
    render(<ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" onResolve={vi.fn()} resolvingCaseId={APPROVAL_CASES_FIXTURE[0].caseId} />);
    const card = screen.getAllByTestId("approval-card")[0];
    expect(card.className).toContain("approval-card-resolving");
    expect(screen.getByRole("button", { name: /approving/i })).toBeDisabled();
  });

  it("clicking Decline tracks the decline flavor of the resolving card and shows a declining label", () => {
    const onResolve = vi.fn();
    const { rerender } = render(
      <ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" onResolve={onResolve} resolvingCaseId={null} />
    );
    const declineButtons = screen.getAllByRole("button", { name: "Decline" });
    fireEvent.click(declineButtons[0]);
    expect(onResolve).toHaveBeenCalledWith(APPROVAL_CASES_FIXTURE[0].caseId, "decline");
    rerender(
      <ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" onResolve={onResolve} resolvingCaseId={APPROVAL_CASES_FIXTURE[0].caseId} />
    );
    const card = screen.getAllByTestId("approval-card")[0];
    expect(card.className).toContain("approval-card-resolving--decline");
    expect(screen.getByRole("button", { name: /declining/i })).toBeDisabled();
  });

  it("the Approve and Decline buttons carry hover/active styling and the shared focus-ring class", () => {
    render(<ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" onResolve={vi.fn()} resolvingCaseId={null} />);
    const approve = screen.getAllByRole("button", { name: "Approve" })[0];
    const decline = screen.getAllByRole("button", { name: "Decline" })[0];
    for (const button of [approve, decline]) {
      expect(button.className).toContain("stacks-focus-ring");
      expect(button.className).toMatch(/hover:/);
      expect(button.className).toMatch(/active:/);
    }
  });

  it("the trust-mode toggle checkbox carries the shared focus-ring class", () => {
    render(<ApprovalInboxView cases={APPROVAL_CASES_FIXTURE} status="ready" onResolve={vi.fn()} resolvingCaseId={null} />);
    const yellowCard = screen.getByText(/Left Hand of Darkness/).closest("[data-testid='approval-card']") as HTMLElement;
    const checkbox = yellowCard.querySelector("input[type='checkbox']");
    expect(checkbox?.className).toContain("stacks-focus-ring");
  });
});
