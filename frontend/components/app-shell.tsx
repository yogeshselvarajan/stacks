import Link from "next/link";
import { Inbox, Calendar, BookOpen, Clock3, ScrollText } from "lucide-react";

type Role = "circulation_staff" | "room_booking_staff" | "ill_coordinator" | "branch_manager";

const NAV_ITEMS = [
  { href: "/approvals", label: "Approval Inbox", Icon: Inbox, countKey: "approvals" as const },
  { href: "/calendar", label: "Calendar", Icon: Calendar, countKey: null },
  { href: "/ill-queue", label: "ILL Queue", Icon: BookOpen, countKey: null },
  { href: "/overdue-queue", label: "Overdue Queue", Icon: Clock3, countKey: null },
  { href: "/audit", label: "Audit Trail", Icon: ScrollText, countKey: null },
];

export function AppShell({
  role,
  pendingCounts,
  activeRoute,
  children,
}: {
  role: Role;
  pendingCounts: { approvals: number };
  activeRoute: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen" style={{ background: "var(--color-bg)" }}>
      <nav
        aria-label="Primary"
        className="w-64 shrink-0 border-r p-4"
        style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
      >
        <ul className="space-y-1">
          {NAV_ITEMS.map(({ href, label, Icon, countKey }) => {
            const count = countKey ? pendingCounts[countKey] : 0;
            const active = activeRoute === href;
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className="stacks-focus-ring flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-[var(--color-bg)] active:bg-[var(--color-border)]"
                  style={{
                    transitionDuration: "var(--motion-duration-feedback)",
                    transitionTimingFunction: "var(--motion-ease-feedback)",
                    color: "var(--color-ink)",
                    background: active ? "var(--color-bg)" : "transparent",
                  }}
                >
                  <span className="flex items-center gap-2">
                    <Icon size={20} aria-hidden="true" />
                    {label}
                  </span>
                  {countKey && count > 0 && (
                    <span
                      data-testid={`${countKey}-count`}
                      className="rounded-full px-2 py-0.5 text-xs font-semibold text-white"
                      style={{ background: "var(--color-tier-red-fill)" }}
                    >
                      {count}
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="flex-1">
        <header
          className="flex items-center justify-between border-b px-6 py-3"
          style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
        >
          <span className="font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Stacks</span>
          <span className="text-sm" style={{ color: "var(--color-ink-muted)" }}>{role.replace(/_/g, " ")}</span>
        </header>
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
