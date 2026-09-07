import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApprovalCaseDetail } from "./approval-case-detail";
import { APPROVAL_CASES_FIXTURE } from "@/lib/fixtures";

const RED_CASE = APPROVAL_CASES_FIXTURE[0];
const YELLOW_CASE = APPROVAL_CASES_FIXTURE[1];

describe("ApprovalCaseDetail", () => {
  it("populated state: shows the case summary and candidate list", () => {
    render(<ApprovalCaseDetail case={RED_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="idle" resolving={false} />);
    expect(screen.getByText(RED_CASE.summary)).toBeInTheDocument();
    expect(screen.getByText("Book Club (recurring)")).toBeInTheDocument();
  });

  it("Edit is constrained to the case's own candidate list (a select, not free text)", () => {
    render(<ApprovalCaseDetail case={RED_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="idle" resolving={false} />);
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    const select = screen.getByLabelText("Choose a different outcome");
    const optionValues = Array.from(select.querySelectorAll("option")).map((o) => (o as HTMLOptionElement).value);
    expect(optionValues).toEqual(RED_CASE.candidates!.map((c) => c.id));
  });

  it("calls onApprove with no edited value on a plain Approve click", () => {
    const onApprove = vi.fn();
    render(<ApprovalCaseDetail case={YELLOW_CASE} onApprove={onApprove} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="idle" resolving={false} />);
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(onApprove).toHaveBeenCalledWith(YELLOW_CASE.caseId);
  });

  it("Decline requires a reason and calls onDecline with it", () => {
    const onDecline = vi.fn();
    render(<ApprovalCaseDetail case={YELLOW_CASE} onApprove={vi.fn()} onDecline={onDecline} onEdit={vi.fn()} actionStatus="idle" resolving={false} />);
    fireEvent.click(screen.getByRole("button", { name: "Decline" }));
    fireEvent.change(screen.getByLabelText("Reason for declining"), { target: { value: "Wrong candidate." } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm decline" }));
    expect(onDecline).toHaveBeenCalledWith(YELLOW_CASE.caseId, "Wrong candidate.");
  });

  it("the Confirm decline button stays disabled until a reason is entered", () => {
    render(<ApprovalCaseDetail case={YELLOW_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="idle" resolving={false} />);
    fireEvent.click(screen.getByRole("button", { name: "Decline" }));
    expect(screen.getByRole("button", { name: "Confirm decline" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Reason for declining"), { target: { value: "Wrong candidate." } });
    expect(screen.getByRole("button", { name: "Confirm decline" })).toBeEnabled();
  });

  it("calls onEdit with the chosen candidate id on Confirm edit", () => {
    const onEdit = vi.fn();
    render(<ApprovalCaseDetail case={RED_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={onEdit} actionStatus="idle" resolving={false} />);
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Choose a different outcome"), { target: { value: RED_CASE.candidates![1].id } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm edit" }));
    expect(onEdit).toHaveBeenCalledWith(RED_CASE.caseId, RED_CASE.candidates![1].id);
  });

  it("loading (submitting) state disables every action button", () => {
    render(<ApprovalCaseDetail case={YELLOW_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="submitting" resolving={false} />);
    expect(screen.getByRole("button", { name: /approving/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Decline" })).toBeDisabled();
  });

  it("error state: shows a specific error message, not a generic one", () => {
    render(<ApprovalCaseDetail case={YELLOW_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="error" resolving={false} />);
    expect(screen.getByText(/could not submit your decision/i)).toBeInTheDocument();
  });

  it("the Approve, Decline, and Edit buttons carry hover/active styling and the shared focus-ring class", () => {
    render(<ApprovalCaseDetail case={RED_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="idle" resolving={false} />);
    const approve = screen.getByRole("button", { name: "Approve" });
    const decline = screen.getByRole("button", { name: "Decline" });
    const edit = screen.getByRole("button", { name: "Edit" });
    for (const button of [approve, decline, edit]) {
      expect(button.className).toContain("stacks-focus-ring");
      expect(button.className).toMatch(/hover:/);
      expect(button.className).toMatch(/active:/);
    }
  });

  it("Edit is not offered when the case has no candidates", () => {
    render(<ApprovalCaseDetail case={YELLOW_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="idle" resolving={false} />);
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull();
  });

  it("YELLOW-tier cases render a trust-mode toggle", () => {
    render(<ApprovalCaseDetail case={YELLOW_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="idle" resolving={false} />);
    expect(screen.getByTestId("trust-mode-toggle")).toBeInTheDocument();
  });

  it("RED-tier cases never render a trust-mode toggle", () => {
    render(<ApprovalCaseDetail case={RED_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="idle" resolving={false} />);
    expect(screen.queryByTestId("trust-mode-toggle")).toBeNull();
  });

  it("carries the resolving cross-fade class only while resolving is true", () => {
    const { container, rerender } = render(
      <ApprovalCaseDetail case={RED_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="idle" resolving={false} />
    );
    expect(container.firstElementChild?.className).not.toContain("approval-detail-resolving");
    rerender(<ApprovalCaseDetail case={RED_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="submitting" resolving={true} />);
    expect(container.firstElementChild?.className).toContain("approval-detail-resolving");
  });

  it("the trust-mode toggle checkbox is disabled while a decision is submitting", () => {
    render(<ApprovalCaseDetail case={YELLOW_CASE} onApprove={vi.fn()} onDecline={vi.fn()} onEdit={vi.fn()} actionStatus="submitting" resolving={true} />);
    expect(screen.getByTestId("trust-mode-toggle").querySelector("input[type='checkbox']")).toBeDisabled();
  });
});
