import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LoginView } from "./login-view";

function renderJudges(overrides: Partial<Parameters<typeof LoginView>[0]> = {}) {
  return render(
    <LoginView
      mode="judges"
      onModeChange={vi.fn()}
      onSignIn={vi.fn()}
      onSignUp={vi.fn()}
      onJudgeLogin={vi.fn()}
      status="idle"
      errorMessage={null}
      {...overrides}
    />
  );
}

describe("LoginView, judges mode (the default)", () => {
  it("shows a one-click continue button, no username/password fields", () => {
    renderJudges();
    expect(screen.getByRole("button", { name: /continue as hackathon judge/i })).toBeEnabled();
    expect(screen.queryByLabelText("Username")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
  });

  it("calls onJudgeLogin when the continue button is clicked", () => {
    const onJudgeLogin = vi.fn();
    renderJudges({ onJudgeLogin });
    fireEvent.click(screen.getByRole("button", { name: /continue as hackathon judge/i }));
    expect(onJudgeLogin).toHaveBeenCalledTimes(1);
  });

  it("loading state disables the button and shows a distinct label", () => {
    renderJudges({ status: "loading" });
    expect(screen.getByRole("button", { name: /signing in/i })).toBeDisabled();
  });

  it("error state shows the specific message", () => {
    renderJudges({ status: "error", errorMessage: "Judge access is temporarily unavailable. Try the Sign in tab instead." });
    expect(screen.getByText("Judge access is temporarily unavailable. Try the Sign in tab instead.")).toBeInTheDocument();
  });

  it("the Judges tab is the first tab and is selected", () => {
    renderJudges();
    const tabs = screen.getAllByRole("tab");
    expect(tabs[0]).toHaveTextContent("Hackathon Judges");
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
  });

  it("clicking the Sign in tab calls onModeChange with signin", () => {
    const onModeChange = vi.fn();
    renderJudges({ onModeChange });
    fireEvent.click(screen.getByRole("tab", { name: "Sign in" }));
    expect(onModeChange).toHaveBeenCalledWith("signin");
  });
});

function renderSignIn(overrides: Partial<Parameters<typeof LoginView>[0]> = {}) {
  return render(
    <LoginView
      mode="signin"
      onModeChange={vi.fn()}
      onSignIn={vi.fn()}
      onSignUp={vi.fn()}
      onJudgeLogin={vi.fn()}
      status="idle"
      errorMessage={null}
      {...overrides}
    />
  );
}

describe("LoginView, sign-in mode", () => {
  it("default state: submit button is enabled and shows its default label", () => {
    renderSignIn();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
  });

  it("loading state: submit button shows a loading label and is disabled", () => {
    renderSignIn({ status: "loading" });
    const button = screen.getByRole("button", { name: /signing in/i });
    expect(button).toBeDisabled();
  });

  it("loading state: inputs are also disabled", () => {
    renderSignIn({ status: "loading" });
    expect(screen.getByLabelText("Username")).toBeDisabled();
    expect(screen.getByLabelText("Password")).toBeDisabled();
  });

  it("error state: shows the specific, plain-language error message, not a generic one", () => {
    renderSignIn({ status: "error", errorMessage: "Incorrect username or password." });
    expect(screen.getByText("Incorrect username or password.")).toBeInTheDocument();
  });

  it("calls onSignIn with the entered username and password", () => {
    const onSignIn = vi.fn();
    renderSignIn({ onSignIn });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "test-branch-manager" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "hunter2" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(onSignIn).toHaveBeenCalledWith("test-branch-manager", "hunter2");
  });

  it("does not show the role picker in sign-in mode", () => {
    renderSignIn();
    expect(screen.queryByText("Role")).not.toBeInTheDocument();
  });

  it("every input and the submit button carry the shared focus-ring class", () => {
    renderSignIn();
    expect(screen.getByLabelText("Username").className).toContain("stacks-focus-ring");
    expect(screen.getByLabelText("Password").className).toContain("stacks-focus-ring");
    expect(screen.getByRole("button", { name: "Sign in" }).className).toContain("stacks-focus-ring");
  });

  it("the submit button carries hover and active styling, not just a default state", () => {
    renderSignIn();
    const button = screen.getByRole("button", { name: "Sign in" });
    expect(button.className).toMatch(/hover:/);
    expect(button.className).toMatch(/active:/);
  });

  it("does not call onSignIn when the fields are empty (required validation)", () => {
    const onSignIn = vi.fn();
    renderSignIn({ onSignIn });
    expect(screen.getByLabelText("Username")).toBeRequired();
    expect(screen.getByLabelText("Password")).toBeRequired();
  });

  it("carries the Stacks wordmark back to /, matching the public site's own mark", () => {
    renderSignIn();
    expect(screen.getByRole("link", { name: "Stacks" })).toHaveAttribute("href", "/");
  });

  it("the login card sits on the surface token with a hairline border, not the canvas background", () => {
    renderSignIn();
    const card = screen.getByTestId("login-card");
    expect(card.style.background).toBe("var(--color-surface)");
    expect(card.style.borderColor).toBe("var(--color-border)");
  });

  it("clicking the Create account tab calls onModeChange with signup", () => {
    const onModeChange = vi.fn();
    renderSignIn({ onModeChange });
    fireEvent.click(screen.getByRole("tab", { name: "Create account" }));
    expect(onModeChange).toHaveBeenCalledWith("signup");
  });
});

function renderSignUp(overrides: Partial<Parameters<typeof LoginView>[0]> = {}) {
  return render(
    <LoginView
      mode="signup"
      onModeChange={vi.fn()}
      onSignIn={vi.fn()}
      onSignUp={vi.fn()}
      onJudgeLogin={vi.fn()}
      status="idle"
      errorMessage={null}
      {...overrides}
    />
  );
}

describe("LoginView, sign-up mode", () => {
  it("shows the role picker with all four roles", () => {
    renderSignUp();
    expect(screen.getByText("Branch manager")).toBeInTheDocument();
    expect(screen.getByText("Room booking staff")).toBeInTheDocument();
    expect(screen.getByText("ILL coordinator")).toBeInTheDocument();
    expect(screen.getByText("Circulation staff")).toBeInTheDocument();
  });

  it("defaults to circulation staff and lets the user pick a different role", () => {
    renderSignUp();
    const branchManagerOption = screen.getByRole("button", { name: /Branch manager/ });
    expect(branchManagerOption).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(branchManagerOption);
    expect(branchManagerOption).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onSignUp with the entered username, password, and selected role", () => {
    const onSignUp = vi.fn();
    renderSignUp({ onSignUp });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "new-demo-user" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "Sup3r$ecret!" } });
    fireEvent.click(screen.getByRole("button", { name: /ILL coordinator/ }));
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(onSignUp).toHaveBeenCalledWith("new-demo-user", "Sup3r$ecret!", "ill_coordinator");
  });

  it("shows a password requirements hint", () => {
    renderSignUp();
    expect(screen.getByText(/uppercase letter, a lowercase letter, a number, and a symbol/)).toBeInTheDocument();
  });

  it("loading state shows a distinct loading label from sign-in", () => {
    renderSignUp({ status: "loading" });
    expect(screen.getByRole("button", { name: /creating account/i })).toBeDisabled();
  });
});
