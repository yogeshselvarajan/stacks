"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LoginView } from "@/components/login-view";
import { login } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/types";

export default function LoginPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(username: string, password: string) {
    setStatus("loading");
    setErrorMessage(null);
    try {
      await login(username, password);
      router.push("/");
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
