import Link from "next/link";
import { Inbox, Calendar, BookOpen, Clock3, ScrollText, Library, Home } from "lucide-react";
import { LiveDot } from "@/components/motion/live-dot";

type Role = "circulation_staff" | "room_booking_staff" | "ill_coordinator" | "branch_manager";

type NavItem = { href: string; label: string; Icon: typeof Inbox; countKey: "approvals" | null };

const HOME_ITEM: NavItem = { href: "/console", label: "Home", Icon: Home, countKey: null };

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

// Home is always visible for every role (handled separately, rendered
// outside NAV_GROUPS). Audit Trail is visible to every role since it's
// read-only evidence, not a write surface, per this plan's own Preamble.
const ROLE_VISIBLE_ROUTES: Record<Role, string[]> = {
  branch_manager: ["/approvals", "/calendar", "/ill-queue", "/overdue-queue", "/audit"],
  room_booking_staff: ["/calendar", "/audit"],
  ill_coordinator: ["/ill-queue", "/audit"],
  circulation_staff: ["/overdue-queue", "/audit"],
};

export function AppShell({
  role,
  tenantName,
  pendingCounts,
  activeRoute,
  caseReviewRole,
  children,
}: {
  role: Role;
  tenantName: string;
  pendingCounts: { approvals: number };
  activeRoute: string;
  caseReviewRole: string | null;
  children: React.ReactNode;
}) {
  const visibleHrefs = new Set(ROLE_VISIBLE_ROUTES[role]);
  if (caseReviewRole) visibleHrefs.add("/approvals");

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

        <ul className="mb-4 space-y-0.5">
          <li>
            <Link
              href={HOME_ITEM.href}
              aria-current={activeRoute === HOME_ITEM.href ? "page" : undefined}
              className="stacks-focus-ring flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-[var(--color-surface-2)] active:bg-[var(--color-border)]"
              style={{
                transitionDuration: "var(--motion-duration-feedback)",
                transitionTimingFunction: "var(--motion-ease-feedback)",
                color: activeRoute === HOME_ITEM.href ? "var(--color-accent)" : "var(--color-ink)",
                background: activeRoute === HOME_ITEM.href ? "var(--color-surface-2)" : "transparent",
                borderLeft: activeRoute === HOME_ITEM.href ? "2px solid var(--color-accent)" : "2px solid transparent",
              }}
            >
              <HOME_ITEM.Icon size={18} aria-hidden="true" />
              {HOME_ITEM.label}
            </Link>
          </li>
        </ul>

        {NAV_GROUPS.map((group) => {
          const visibleItems = group.items.filter((item) => visibleHrefs.has(item.href));
          if (visibleItems.length === 0) return null;
          return (
          <div key={group.label} className="mb-4">
            <p
              className="mb-1.5 px-1 text-[10px] font-semibold uppercase tracking-wide"
              style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-muted)" }}
            >
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {visibleItems.map(({ href, label, Icon, countKey }) => {
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
          );
        })}

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
          <span className="flex items-center gap-1.5 font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
            <Library size={16} aria-hidden="true" style={{ color: "var(--color-accent)" }} />
            Stacks
          </span>
          <span className="text-sm" style={{ color: "var(--color-ink-muted)" }}>{role.replace(/_/g, " ")}</span>
        </header>
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
