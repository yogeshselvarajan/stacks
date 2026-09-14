"use client";

import { useState } from "react";
import Link from "next/link";
import { BookOpen, Calendar, Clock3, Gavel, Library, ShieldCheck } from "lucide-react";
import { Reveal } from "@/components/motion/reveal";
import { LiveDot } from "@/components/motion/live-dot";
import { SignupRole } from "@/lib/api/auth";

type Mode = "judges" | "signin" | "signup";

const ROLE_OPTIONS: { value: SignupRole; label: string; description: string; Icon: typeof Calendar }[] = [
  { value: "branch_manager", label: "Branch manager", description: "Sees every workflow, approves every tier", Icon: ShieldCheck },
  { value: "room_booking_staff", label: "Room booking staff", description: "Resolves room-booking conflicts", Icon: Calendar },
  { value: "ill_coordinator", label: "ILL coordinator", description: "Routes interlibrary-loan requests", Icon: BookOpen },
  { value: "circulation_staff", label: "Circulation staff", description: "Chases overdue items", Icon: Clock3 },
];

const MODE_LABELS: Record<Mode, string> = {
  judges: "Hackathon Judges",
  signin: "Sign in",
  signup: "Create account",
};

function ModeToggle({ mode, onChange }: { mode: Mode; onChange: (mode: Mode) => void }) {
  return (
    <div
      role="tablist"
      aria-label="Hackathon judge access, sign in, or create an account"
      className="mb-6 grid grid-cols-3 gap-1 rounded-lg border p-1"
      style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}
    >
      {(["judges", "signin", "signup"] as const).map((value) => (
        <button
          key={value}
          type="button"
          role="tab"
          aria-selected={mode === value}
          onClick={() => onChange(value)}
          className="stacks-focus-ring rounded-md px-2 py-2 text-sm font-semibold transition-colors"
          style={{
            background: mode === value ? "var(--color-accent)" : "transparent",
            color: mode === value ? "var(--color-fill-text)" : "var(--color-ink-muted)",
            transitionDuration: "var(--motion-duration-feedback)",
          }}
        >
          {MODE_LABELS[value]}
        </button>
      ))}
    </div>
  );
}

function TextField({
  id, label, type, autoComplete, value, onChange, disabled,
}: {
  id: string; label: string; type: string; autoComplete: string;
  value: string; onChange: (v: string) => void; disabled: boolean;
}) {
  return (
    <div className="mb-3">
      <label htmlFor={id} className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        {label}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        autoComplete={autoComplete}
        required
        className="stacks-focus-ring w-full rounded border px-3 py-2 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60"
        style={{
          borderColor: "var(--color-border)",
          background: "var(--color-surface-2)",
          color: "var(--color-ink)",
          transitionDuration: "var(--motion-duration-feedback)",
          transitionTimingFunction: "var(--motion-ease-feedback)",
        }}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      />
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="mb-3 rounded px-3 py-2 text-sm"
      style={{ color: "var(--color-tier-red-text)", background: "var(--color-tier-red-bg)" }}
    >
      {message}
    </p>
  );
}

export function LoginView({
  mode,
  onModeChange,
  onSignIn,
  onSignUp,
  onJudgeLogin,
  status,
  errorMessage,
}: {
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  onSignIn: (username: string, password: string) => void;
  onSignUp: (username: string, password: string, role: SignupRole) => void;
  onJudgeLogin: () => void;
  status: "idle" | "loading" | "error";
  errorMessage: string | null;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<SignupRole>("circulation_staff");
  const busy = status === "loading";

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (mode === "signin") onSignIn(username, password);
    else if (mode === "signup") onSignUp(username, password, role);
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-6 py-16" style={{ background: "var(--color-bg)" }}>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[560px]"
        style={{ background: "radial-gradient(closest-side, color-mix(in srgb, var(--color-accent) 14%, transparent), transparent)" }}
      />

      <div className="grid w-full max-w-4xl items-center gap-14 lg:grid-cols-2">
        <Reveal>
          <div className="max-w-sm">
            <Link href="/" className="stacks-focus-ring inline-flex items-center gap-2 rounded-md">
              <Library size={20} aria-hidden="true" style={{ color: "var(--color-accent)" }} />
              <span className="font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
                Stacks
              </span>
            </Link>

            <span
              className="mt-8 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide"
              style={{ borderColor: "var(--color-border)", color: "var(--color-ink-muted)", fontFamily: "var(--font-mono)" }}
            >
              <LiveDot />
              Real Cognito sign-in, real AWS underneath
            </span>

            <h1
              className="mt-5 text-3xl leading-tight"
              style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}
            >
              Where library staff work the exception queue.
            </h1>

            <p className="mt-4 text-base leading-relaxed" style={{ color: "var(--color-ink-muted)" }}>
              Room-booking conflicts, ambiguous interlibrary-loan requests, and overdue
              chasing, resolved automatically when it&apos;s safe and escalated to a human
              the moment it isn&apos;t.
            </p>

            <p className="mt-6 text-sm" style={{ color: "var(--color-ink-faint)" }}>
              Judging the hackathon? Use the Hackathon Judges tab on the right for
              one-click access, no password needed. Exploring on your own? Create an
              account and pick a role, and you&apos;re signed in immediately with no
              email verification step.
            </p>
          </div>
        </Reveal>

        <Reveal delayMs={80}>
          <div
            data-testid="login-card"
            className="w-full rounded-lg border p-6"
            style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", boxShadow: "var(--shadow-floating)" }}
          >
            <ModeToggle mode={mode} onChange={onModeChange} />

            {mode === "judges" ? (
              <div>
                <div className="mb-4 flex items-center gap-2">
                  <Gavel size={18} aria-hidden="true" style={{ color: "var(--color-accent)" }} />
                  <h2 className="text-lg font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
                    Hackathon Judges
                  </h2>
                </div>
                <p className="mb-4 text-sm leading-relaxed" style={{ color: "var(--color-ink-muted)" }}>
                  One click, no password required. This signs you in with full,
                  real access to Stacks (every workflow, every approval tier)
                  against the real deployed AWS infrastructure. No credentials are
                  ever sent from your browser; the sign-in happens entirely on the
                  server.
                </p>
                {status === "error" && errorMessage && <ErrorBanner message={errorMessage} />}
                <button
                  type="button"
                  onClick={onJudgeLogin}
                  disabled={busy}
                  className="stacks-focus-ring flex w-full items-center justify-center gap-2 rounded px-4 py-2.5 text-sm font-semibold transition-colors hover:bg-[var(--color-accent-hover)] active:bg-[var(--color-accent-hover)] disabled:cursor-not-allowed disabled:opacity-60"
                  style={{
                    background: "var(--color-accent)",
                    color: "var(--color-fill-text)",
                    transitionDuration: "var(--motion-duration-feedback)",
                    transitionTimingFunction: "var(--motion-ease-feedback)",
                  }}
                >
                  <Gavel size={16} aria-hidden="true" />
                  {busy ? "Signing in..." : "Continue as Hackathon Judge"}
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                <h2 className="mb-4 text-lg font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
                  {mode === "signin" ? "Sign in" : "Create your account"}
                </h2>

                <TextField id="username" label="Username" type="text" autoComplete="username" value={username} onChange={setUsername} disabled={busy} />
                <TextField
                  id="password"
                  label="Password"
                  type="password"
                  autoComplete={mode === "signin" ? "current-password" : "new-password"}
                  value={password}
                  onChange={setPassword}
                  disabled={busy}
                />
                {mode === "signup" && (
                  <p className="mb-3 -mt-2 text-xs" style={{ color: "var(--color-ink-faint)" }}>
                    At least 8 characters, with an uppercase letter, a lowercase letter, a number, and a symbol.
                  </p>
                )}

                {mode === "signup" && (
                  <fieldset className="mb-4">
                    <legend className="mb-2 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
                      Role
                    </legend>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {ROLE_OPTIONS.map(({ value, label, description, Icon }) => {
                        const selected = role === value;
                        return (
                          <button
                            key={value}
                            type="button"
                            aria-pressed={selected}
                            onClick={() => setRole(value)}
                            disabled={busy}
                            className="stacks-focus-ring flex items-start gap-2 rounded-md border p-2.5 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60"
                            style={{
                              borderColor: selected ? "var(--color-accent)" : "var(--color-border)",
                              background: selected ? "color-mix(in srgb, var(--color-accent) 10%, var(--color-surface-2))" : "var(--color-surface-2)",
                              transitionDuration: "var(--motion-duration-feedback)",
                            }}
                          >
                            <Icon size={16} aria-hidden="true" style={{ color: selected ? "var(--color-accent)" : "var(--color-ink-muted)", marginTop: 2 }} />
                            <span>
                              <span className="block text-sm font-medium" style={{ color: "var(--color-ink)" }}>{label}</span>
                              <span className="block text-xs" style={{ color: "var(--color-ink-faint)" }}>{description}</span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </fieldset>
                )}

                {status === "error" && errorMessage && <ErrorBanner message={errorMessage} />}

                <button
                  type="submit"
                  disabled={busy}
                  className="stacks-focus-ring w-full rounded px-4 py-2 text-sm font-medium transition-colors hover:bg-[var(--color-accent-hover)] active:bg-[var(--color-accent-hover)] disabled:cursor-not-allowed disabled:opacity-60"
                  style={{
                    background: "var(--color-accent)",
                    color: "var(--color-fill-text)",
                    transitionDuration: "var(--motion-duration-feedback)",
                    transitionTimingFunction: "var(--motion-ease-feedback)",
                  }}
                >
                  {busy ? (mode === "signin" ? "Signing in..." : "Creating account...") : mode === "signin" ? "Sign in" : "Create account"}
                </button>
              </form>
            )}
          </div>
        </Reveal>
      </div>
    </div>
  );
}
