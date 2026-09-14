import Link from "next/link";
import { Inbox, Calendar, BookOpen, Clock3, ScrollText, Library } from "lucide-react";
import { LiveDot } from "@/components/motion/live-dot";

type Role = "circulation_staff" | "room_booking_staff" | "ill_coordinator" | "branch_manager";

type NavItem = { href: string; label: string; Icon: typeof Inbox; countKey: "approvals" | null };

const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "Workflows",
    items: [
      { href: "/approvals", label: "Approval Inbox", Icon: Inbox, countKey: "approvals" },
      { href: "/calendar", label: "Calendar", Icon: Calendar, countKey: null },
      { href: "/ill-queue", label: "ILL Queue", Icon: BookOpen, countKey: null },
      { href: "/overdue-queue", label: "Overdue Queue", Icon: Clock3, countKey: null },
    ],
  },
  {
    label: "Records",
    items: [{ href: "/audit", label: "Audit Trail", Icon: ScrollText, countKey: null }],
  },
];

export function AppShell({
  role,
  tenantName,
  pendingCounts,
  activeRoute,
  children,
}: {
  role: Role;
  tenantName: string;
  pendingCounts: { approvals: number };
  activeRoute: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen" style={{ background: "var(--color-bg)" }}>
      <nav
        aria-label="Primary"
        className="w-52 shrink-0 border-r p-3"
        style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
      >
        <div className="mb-4 flex items-center gap-2 px-1">
          <Library size={18} aria-hidden="true" style={{ color: "var(--color-accent)" }} />
          <span className="text-sm font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
            {tenantName}
          </span>
        </div>

        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-4">
            <p
              className="mb-1.5 px-1 text-[10px] font-semibold uppercase tracking-wide"
              style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-muted)" }}
            >
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {group.items.map(({ href, label, Icon, countKey }) => {
                const count = countKey ? pendingCounts[countKey] : 0;
                const active = activeRoute === href;
                return (
                  <li key={href}>
                    <Link
                      href={href}
                      aria-current={active ? "page" : undefined}
                      className="stacks-focus-ring flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-[var(--color-surface-2)] active:bg-[var(--color-border)]"
                      style={{
                        transitionDuration: "var(--motion-duration-feedback)",
                        transitionTimingFunction: "var(--motion-ease-feedback)",
                        color: active ? "var(--color-accent)" : "var(--color-ink)",
                        background: active ? "var(--color-surface-2)" : "transparent",
                        borderLeft: active ? "2px solid var(--color-accent)" : "2px solid transparent",
                      }}
                    >
                      <span className="flex items-center gap-2">
                        <Icon size={18} aria-hidden="true" />
                        {label}
                      </span>
                      {countKey && count > 0 && (
                        <span
                          data-testid={`${countKey}-count`}
                          className="rounded-full px-2 py-0.5 text-xs font-semibold"
                          style={{ background: "var(--color-tier-red-fill)", color: "var(--color-fill-text)" }}
                        >
                          {count}
                        </span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}

        <div className="mt-2 border-t pt-3" style={{ borderColor: "var(--color-border)" }}>
          <p className="mb-2 flex items-center gap-1.5 px-1 text-xs" style={{ color: "var(--color-ink-faint)" }}>
            <LiveDot color="var(--color-tier-green-fill)" />
            Operational
          </p>
          <a
            href="https://agentsforhumans.devpost.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="stacks-focus-ring flex items-center rounded-md px-3 py-2 text-xs transition-colors hover:bg-[var(--color-surface-2)] active:bg-[var(--color-border)]"
            style={{
              color: "var(--color-ink-faint)",
              transitionDuration: "var(--motion-duration-feedback)",
              transitionTimingFunction: "var(--motion-ease-feedback)",
            }}
          >
            Built for Agents for Humans, Good Neighbor Agents
          </a>
        </div>
      </nav>
      <div className="flex-1">
        <header
          className="flex items-center justify-between border-b px-6 py-3"
          style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
        >
          <span className="font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>Stacks</span>
          <span className="text-sm" style={{ color: "var(--color-ink-muted)" }}>{role.replace(/_/g, " ")}</span>
        </header>
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
