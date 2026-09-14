"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getSession } from "@/lib/api/auth";

// Every authenticated console route calls this once on mount. It never
// duplicates the check -- one hook, one place the redirect-to-login-and-back
// behavior lives. A failed session check (no cookie, expired session) sends
// the user to /login with the page they were trying to reach preserved, so
// signing in returns them to it instead of always landing on /console.
export function useRequireSession() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    let cancelled = false;
    getSession().catch(() => {
      if (!cancelled) router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
    });
    return () => {
      cancelled = true;
    };
  }, [router, pathname]);
}
