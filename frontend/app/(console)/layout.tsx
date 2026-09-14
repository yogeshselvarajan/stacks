"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { AppShell } from "@/components/app-shell";
import { getApprovals } from "@/lib/api/approvals";
import { getSession } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/types";
import { useRequireSession } from "@/lib/use-require-session";
import { DURATION, EASE, prefersReducedMotion } from "@/lib/motion-tokens";
import { usePolling } from "@/lib/use-polling";

type Role = "circulation_staff" | "room_booking_staff" | "ill_coordinator" | "branch_manager";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  useRequireSession();
  const router = useRouter();
  const pathname = usePathname();
  const [approvalsCount, setApprovalsCount] = useState(0);
  const [session, setSession] = useState<{ role: string; caseReviewRole: string | null } | null>(null);

  function fetchApprovalsCount() {
    getApprovals()
      .then((cases) => setApprovalsCount(cases.filter((c) => c.tier !== "GREEN").length))
      .catch((err) => {
        // I6 (final review fix round): an expired session otherwise turns
        // every 15-second poll into a silent, permanently-repeating 401
        // with no recovery. Only a 401 is recoverable by redirecting to
        // /login -- the nav badge is supplementary for every other error,
        // so it just stays at 0 rather than blocking the page.
        if (err instanceof ApiError && err.status === 401) {
          router.push("/login");
        }
      });
  }

  useEffect(() => {
    fetchApprovalsCount();
  }, []);

  usePolling(fetchApprovalsCount, 15000);

  useEffect(() => {
    getSession().then(setSession).catch(() => {});
  }, []);

  return (
    <AppShell
      role={(session?.role ?? "branch_manager") as Role}
      tenantName="Central Branch"
      pendingCounts={{ approvals: approvalsCount }}
      activeRoute={pathname}
      caseReviewRole={session?.caseReviewRole ?? null}
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
