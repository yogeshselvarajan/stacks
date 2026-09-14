"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, LogOut } from "lucide-react";
import { logout } from "@/lib/api/auth";

function roleLabel(role: string): string {
  return role.replace(/_/g, " ");
}

function roleInitial(role: string): string {
  return role.charAt(0).toUpperCase();
}

export function AccountMenu({ role, tenantName }: { role: string; tenantName: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await logout();
    } catch {
      // A failed logout call still leaves the user wanting out -- redirect
      // regardless, matching the cookie's own short lifetime as the
      // fallback: even an unreachable BFF can't keep a stale session valid
      // past its own expiry.
    }
    router.push("/login");
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="stacks-focus-ring flex items-center gap-2 rounded-full border py-1 pl-1 pr-2.5 text-sm transition-colors hover:bg-[var(--color-surface-2)]"
        style={{ borderColor: "var(--color-border)", transitionDuration: "var(--motion-duration-feedback)" }}
      >
        <span
          aria-hidden="true"
          className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold"
          style={{ background: "var(--color-accent)", color: "var(--color-fill-text)" }}
        >
          {roleInitial(role)}
        </span>
        <span style={{ color: "var(--color-ink)" }}>{roleLabel(role)}</span>
        <ChevronDown size={14} aria-hidden="true" style={{ color: "var(--color-ink-muted)" }} />
      </button>

      {open && (
        <>
          {/* Click-outside-to-close: a full-viewport, invisible layer under
              the menu itself rather than a document-level listener, so
              closing needs no effect/cleanup wiring. */}
          <button
            type="button"
            aria-label="Close menu"
            className="fixed inset-0 z-10 cursor-default"
            style={{ background: "transparent" }}
            onClick={() => setOpen(false)}
          />
          <div
            role="menu"
            className="absolute right-0 z-20 mt-2 w-56 rounded-lg border p-1.5"
            style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", boxShadow: "var(--shadow-floating)" }}
          >
            <div className="border-b px-2.5 py-2" style={{ borderColor: "var(--color-border)" }}>
              <p className="text-sm font-medium" style={{ color: "var(--color-ink)" }}>{roleLabel(role)}</p>
              <p className="text-xs" style={{ color: "var(--color-ink-faint)" }}>{tenantName}</p>
            </div>
            <button
              type="button"
              role="menuitem"
              onClick={handleSignOut}
              disabled={signingOut}
              className="stacks-focus-ring mt-1 flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm font-medium transition-colors hover:bg-[var(--color-surface-2)] disabled:cursor-not-allowed disabled:opacity-60"
              style={{ color: "var(--color-tier-red-text)", transitionDuration: "var(--motion-duration-feedback)" }}
            >
              <LogOut size={16} aria-hidden="true" />
              {signingOut ? "Signing out..." : "Sign out"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
