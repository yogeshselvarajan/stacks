"use client";

import { useState } from "react";

export function LoginView({
  onSubmit,
  status,
  errorMessage,
}: {
  onSubmit: (username: string, password: string) => void;
  status: "idle" | "loading" | "error";
  errorMessage: string | null;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const busy = status === "loading";

  return (
    <div className="flex min-h-screen items-center justify-center" style={{ background: "var(--color-bg)" }}>
      <form
        className="w-80 rounded-lg border p-6"
        style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
        onSubmit={(e) => {
          e.preventDefault();
          if (!busy) onSubmit(username, password);
        }}
      >
        <h1 className="mb-4 text-xl font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
          Stacks
        </h1>

        <label htmlFor="username" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
          Username
        </label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          required
          className="stacks-focus-ring mb-3 w-full rounded border px-3 py-2 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          style={{
            borderColor: "var(--color-border)",
            background: "var(--color-bg)",
            color: "var(--color-ink)",
            transitionDuration: "var(--motion-duration-feedback)",
            transitionTimingFunction: "var(--motion-ease-feedback)",
          }}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={busy}
        />

        <label htmlFor="password" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="stacks-focus-ring mb-4 w-full rounded border px-3 py-2 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          style={{
            borderColor: "var(--color-border)",
            background: "var(--color-bg)",
            color: "var(--color-ink)",
            transitionDuration: "var(--motion-duration-feedback)",
            transitionTimingFunction: "var(--motion-ease-feedback)",
          }}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={busy}
        />

        {status === "error" && errorMessage && (
          <p
            role="alert"
            className="mb-3 rounded px-3 py-2 text-sm"
            style={{ color: "var(--color-tier-red-text)", background: "var(--color-tier-red-bg)" }}
          >
            {errorMessage}
          </p>
        )}

        <button
          type="submit"
          disabled={busy}
          className="stacks-focus-ring w-full rounded px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-hover)] active:bg-[var(--color-accent-hover)] disabled:cursor-not-allowed disabled:opacity-60"
          style={{
            background: "var(--color-accent)",
            transitionDuration: "var(--motion-duration-feedback)",
            transitionTimingFunction: "var(--motion-ease-feedback)",
          }}
        >
          {busy ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
