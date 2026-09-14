"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { AppShell } from "@/components/app-shell";
import { getApprovals } from "@/lib/api/approvals";
import { useRequireSession } from "@/lib/use-require-session";
import { DURATION, EASE, prefersReducedMotion } from "@/lib/motion-tokens";

type Role = "circulation_staff" | "room_booking_staff" | "ill_coordinator" | "branch_manager";

// One role per route, matching each page's previous per-page AppShell prop --
// preserved here rather than re-derived, now that the shell renders once for
// the whole group instead of once per page.
const ROLE_BY_ROUTE: Record<string, Role> = {
  "/console": "branch_manager",
  "/calendar": "room_booking_staff",
  "/ill-queue": "ill_coordinator",
  "/overdue-queue": "circulation_staff",
  "/audit": "branch_manager",
};

function roleForPathname(pathname: string): Role {
  if (pathname.startsWith("/audit")) return ROLE_BY_ROUTE["/audit"];
  return ROLE_BY_ROUTE[pathname] ?? "branch_manager";
}

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  useRequireSession();
  const pathname = usePathname();
  const [approvalsCount, setApprovalsCount] = useState(0);

  useEffect(() => {
    getApprovals()
      .then((cases) => setApprovalsCount(cases.filter((c) => c.tier !== "GREEN").length))
      .catch(() => {
        // The nav badge is supplementary -- a failed fetch here should never
        // block the page itself from rendering, so it just stays at 0.
      });
  }, []);

  return (
    <AppShell
      role={roleForPathname(pathname)}
      tenantName="Central Branch"
      pendingCounts={{ approvals: approvalsCount }}
      activeRoute={pathname}
    >
      <AnimatePresence mode="wait">
        <motion.div
          key={pathname}
          initial={prefersReducedMotion() ? false : { opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={prefersReducedMotion() ? undefined : { opacity: 0 }}
          transition={{ duration: DURATION.normal, ease: EASE.ui }}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </AppShell>
  );
}
