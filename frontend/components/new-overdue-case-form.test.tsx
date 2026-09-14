import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { NewOverdueCaseForm } from "./new-overdue-case-form";
import * as overdueQueueApi from "@/lib/api/overdue-queue";

vi.mock("@/lib/api/overdue-queue", async () => {
  const actual = await vi.importActual<typeof overdueQueueApi>("@/lib/api/overdue-queue");
  return { ...actual, createOverdueCase: vi.fn() };
});

describe("NewOverdueCaseForm", () => {
  beforeEach(() => {
    vi.mocked(overdueQueueApi.createOverdueCase).mockReset();
  });

  it("starts collapsed, showing only the entry point", () => {
    render(<NewOverdueCaseForm />);
    expect(screen.getByRole("button", { name: /new overdue case/i })).toBeInTheDocument();
    expect(screen.queryByLabelText("Patron ID")).toBeNull();
  });

  it("expands into a form when the entry point is clicked", () => {
    render(<NewOverdueCaseForm />);
    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    expect(screen.getByLabelText("Patron ID")).toBeInTheDocument();
    expect(screen.getByLabelText("Item ID")).toBeInTheDocument();
    expect(screen.getByLabelText("Item type")).toBeInTheDocument();
    expect(screen.getByLabelText("Days overdue")).toBeInTheDocument();
    expect(screen.getByLabelText("Flag as a sensitive account (e.g. a minor)")).toBeInTheDocument();
  });

  it("submits the entered values and shows a real processing state, not a spinner", async () => {
    vi.mocked(overdueQueueApi.createOverdueCase).mockImplementation(
      () => new Promise(() => {}) // never resolves during this assertion
    );
    render(<NewOverdueCaseForm />);
    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    fireEvent.change(screen.getByLabelText("Patron ID"), { target: { value: "patron_x" } });
    fireEvent.change(screen.getByLabelText("Item ID"), { target: { value: "item_1" } });
    fireEvent.change(screen.getByLabelText("Item type"), { target: { value: "book" } });
    fireEvent.change(screen.getByLabelText("Days overdue"), { target: { value: "14" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText(/submitting to stacks/i)).toBeInTheDocument();
    expect(overdueQueueApi.createOverdueCase).toHaveBeenCalledWith({
      patronId: "patron_x",
      itemId: "item_1",
      itemType: "book",
      daysOverdue: 14,
      sensitivityFlag: false,
    });
  });

  it("submits the sensitivity flag when the checkbox is checked", async () => {
    vi.mocked(overdueQueueApi.createOverdueCase).mockImplementation(() => new Promise(() => {}));
    render(<NewOverdueCaseForm />);
    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    fireEvent.change(screen.getByLabelText("Patron ID"), { target: { value: "patron_x" } });
    fireEvent.change(screen.getByLabelText("Item ID"), { target: { value: "item_1" } });
    fireEvent.change(screen.getByLabelText("Item type"), { target: { value: "book" } });
    fireEvent.change(screen.getByLabelText("Days overdue"), { target: { value: "14" } });
    fireEvent.click(screen.getByLabelText("Flag as a sensitive account (e.g. a minor)"));
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() =>
      expect(overdueQueueApi.createOverdueCase).toHaveBeenCalledWith({
        patronId: "patron_x",
        itemId: "item_1",
        itemType: "book",
        daysOverdue: 14,
        sensitivityFlag: true,
      })
    );
  });

  it("shows a link into the Approval Inbox when the case lands as pending approval", async () => {
    vi.mocked(overdueQueueApi.createOverdueCase).mockResolvedValue({
      circulationRecordId: "circ_abc123", status: "pending_approval", outcome: null,
    });
    render(<NewOverdueCaseForm />);
    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    fireEvent.change(screen.getByLabelText("Patron ID"), { target: { value: "patron_x" } });
    fireEvent.change(screen.getByLabelText("Item ID"), { target: { value: "item_1" } });
    fireEvent.change(screen.getByLabelText("Item type"), { target: { value: "book" } });
    fireEvent.change(screen.getByLabelText("Days overdue"), { target: { value: "14" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    const link = await screen.findByRole("link", { name: /review in approval inbox/i });
    expect(link).toHaveAttribute("href", "/approvals/circ_abc123");
  });

  it("shows a resolved message, not a pending-approval link, when the case auto-resolves", async () => {
    vi.mocked(overdueQueueApi.createOverdueCase).mockResolvedValue({
      circulationRecordId: "circ_def456", status: "resolved", outcome: "committed",
    });
    render(<NewOverdueCaseForm />);
    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    fireEvent.change(screen.getByLabelText("Patron ID"), { target: { value: "patron_y" } });
    fireEvent.change(screen.getByLabelText("Item ID"), { target: { value: "item_2" } });
    fireEvent.change(screen.getByLabelText("Item type"), { target: { value: "dvd" } });
    fireEvent.change(screen.getByLabelText("Days overdue"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText(/resolved automatically/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /review in approval inbox/i })).toBeNull();
  });

  it("shows a plain-language error and lets the user try again on failure", async () => {
    vi.mocked(overdueQueueApi.createOverdueCase).mockRejectedValue(new Error("network down"));
    render(<NewOverdueCaseForm />);
    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    fireEvent.change(screen.getByLabelText("Patron ID"), { target: { value: "patron_z" } });
    fireEvent.change(screen.getByLabelText("Item ID"), { target: { value: "item_3" } });
    fireEvent.change(screen.getByLabelText("Item type"), { target: { value: "book" } });
    fireEvent.change(screen.getByLabelText("Days overdue"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/couldn't submit/i));
  });

  it("calls onCreated after a successful submission", async () => {
    const onCreated = vi.fn();
    vi.mocked(overdueQueueApi.createOverdueCase).mockResolvedValue({
      circulationRecordId: "circ_ghi789", status: "resolved", outcome: "committed",
    });
    render(<NewOverdueCaseForm onCreated={onCreated} />);
    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    fireEvent.change(screen.getByLabelText("Patron ID"), { target: { value: "patron_z" } });
    fireEvent.change(screen.getByLabelText("Item ID"), { target: { value: "item_3" } });
    fireEvent.change(screen.getByLabelText("Item type"), { target: { value: "book" } });
    fireEvent.change(screen.getByLabelText("Days overdue"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() => expect(onCreated).toHaveBeenCalled());
  });

  it("shows a could-not-process message when case creation succeeds but agent invocation fails", async () => {
    vi.mocked(overdueQueueApi.createOverdueCase).mockResolvedValue({
      circulationRecordId: "circ_fail1", status: "agent_invocation_failed", outcome: null,
    });
    render(<NewOverdueCaseForm />);
    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    fireEvent.change(screen.getByLabelText("Patron ID"), { target: { value: "patron_x" } });
    fireEvent.change(screen.getByLabelText("Item ID"), { target: { value: "item_1" } });
    fireEvent.change(screen.getByLabelText("Item type"), { target: { value: "book" } });
    fireEvent.change(screen.getByLabelText("Days overdue"), { target: { value: "14" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText(/could not process it yet/i)).toBeInTheDocument();
  });

  it("shows a needs-attention message when the case is created but not completed automatically", async () => {
    vi.mocked(overdueQueueApi.createOverdueCase).mockResolvedValue({
      circulationRecordId: "circ_needs1", status: "needs_attention", outcome: "blocked_missing_approval",
    });
    render(<NewOverdueCaseForm />);
    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    fireEvent.change(screen.getByLabelText("Patron ID"), { target: { value: "patron_x" } });
    fireEvent.change(screen.getByLabelText("Item ID"), { target: { value: "item_1" } });
    fireEvent.change(screen.getByLabelText("Item type"), { target: { value: "book" } });
    fireEvent.change(screen.getByLabelText("Days overdue"), { target: { value: "14" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(
      await screen.findByText(/could not complete it automatically.*check the overdue queue/i)
    ).toBeInTheDocument();
  });

  it("resets the draft fields when Cancel is clicked, unlike a stale reopen", () => {
    render(<NewOverdueCaseForm />);
    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    fireEvent.change(screen.getByLabelText("Patron ID"), { target: { value: "patron_x" } });
    fireEvent.click(screen.getByLabelText("Flag as a sensitive account (e.g. a minor)"));
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    expect(screen.getByLabelText("Patron ID")).toHaveValue("");
    expect(screen.getByLabelText("Flag as a sensitive account (e.g. a minor)")).not.toBeChecked();
  });

  it("every input and the submit button carry the shared focus-ring class", () => {
    render(<NewOverdueCaseForm />);
    fireEvent.click(screen.getByRole("button", { name: /new overdue case/i }));
    expect(screen.getByLabelText("Patron ID").className).toContain("stacks-focus-ring");
    expect(screen.getByLabelText("Item ID").className).toContain("stacks-focus-ring");
    expect(screen.getByLabelText("Item type").className).toContain("stacks-focus-ring");
    expect(screen.getByLabelText("Days overdue").className).toContain("stacks-focus-ring");
    expect(screen.getByRole("button", { name: /submit/i }).className).toContain("stacks-focus-ring");
  });
});
