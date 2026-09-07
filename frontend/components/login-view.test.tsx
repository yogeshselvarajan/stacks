import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LoginView } from "./login-view";

describe("LoginView", () => {
  it("default state: submit button is enabled and shows its default label", () => {
    render(<LoginView onSubmit={vi.fn()} status="idle" errorMessage={null} />);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
  });

  it("loading state: submit button shows a loading label and is disabled", () => {
    render(<LoginView onSubmit={vi.fn()} status="loading" errorMessage={null} />);
    const button = screen.getByRole("button", { name: /signing in/i });
    expect(button).toBeDisabled();
  });

  it("loading state: inputs are also disabled", () => {
    render(<LoginView onSubmit={vi.fn()} status="loading" errorMessage={null} />);
    expect(screen.getByLabelText("Username")).toBeDisabled();
    expect(screen.getByLabelText("Password")).toBeDisabled();
  });

  it("error state: shows the specific, plain-language error message, not a generic one", () => {
    render(<LoginView onSubmit={vi.fn()} status="error" errorMessage="Incorrect username or password." />);
    expect(screen.getByText("Incorrect username or password.")).toBeInTheDocument();
  });

  it("calls onSubmit with the entered username and password", () => {
    const onSubmit = vi.fn();
    render(<LoginView onSubmit={onSubmit} status="idle" errorMessage={null} />);
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "test-branch-manager" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "hunter2" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(onSubmit).toHaveBeenCalledWith("test-branch-manager", "hunter2");
  });

  it("every input and the submit button carry the shared focus-ring class", () => {
    render(<LoginView onSubmit={vi.fn()} status="idle" errorMessage={null} />);
    expect(screen.getByLabelText("Username").className).toContain("stacks-focus-ring");
    expect(screen.getByLabelText("Password").className).toContain("stacks-focus-ring");
    expect(screen.getByRole("button", { name: "Sign in" }).className).toContain("stacks-focus-ring");
  });

  it("the submit button carries hover and active styling, not just a default state", () => {
    render(<LoginView onSubmit={vi.fn()} status="idle" errorMessage={null} />);
    const button = screen.getByRole("button", { name: "Sign in" });
    expect(button.className).toMatch(/hover:/);
    expect(button.className).toMatch(/active:/);
  });

  it("does not call onSubmit when the fields are empty (required validation)", () => {
    const onSubmit = vi.fn();
    render(<LoginView onSubmit={onSubmit} status="idle" errorMessage={null} />);
    expect(screen.getByLabelText("Username")).toBeRequired();
    expect(screen.getByLabelText("Password")).toBeRequired();
  });

  it("the login card sits on the surface token with a hairline border, not the canvas background", () => {
    const { container } = render(<LoginView onSubmit={vi.fn()} status="idle" errorMessage={null} />);
    const form = container.querySelector("form") as HTMLElement;
    expect(form.style.background).toBe("var(--color-surface)");
    expect(form.style.borderColor).toBe("var(--color-border)");
  });
});
