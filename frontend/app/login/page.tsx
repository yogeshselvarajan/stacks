"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LoginView } from "@/components/login-view";
import { login } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/types";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(username: string, password: string) {
    setStatus("loading");
    setErrorMessage(null);
    try {
      await login(username, password);
      const redirectTarget = searchParams.get("redirect");
      const isSafeInternalPath = !!redirectTarget && redirectTarget.startsWith("/") && !redirectTarget.startsWith("//");
      router.push(isSafeInternalPath ? redirectTarget! : "/console");
    } catch (err) {
      setStatus("error");
      setErrorMessage(
        err instanceof ApiError && err.status === 401
          ? "Incorrect username or password."
          : "Sign in failed. Try again."
      );
    }
  }

  return <LoginView onSubmit={handleSubmit} status={status} errorMessage={errorMessage} />;
}

export default function LoginPage() {
  useEffect(() => {
    document.title = "Stacks | Sign in";
  }, []);

  return (
    <Suspense fallback={<LoginView onSubmit={() => {}} status="idle" errorMessage={null} />}>
      <LoginForm />
    </Suspense>
  );
}
