"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LoginView } from "@/components/login-view";
import { login, signup, SignupRole } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/types";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  function goToConsole() {
    const redirectTarget = searchParams.get("redirect");
    const isSafeInternalPath = !!redirectTarget && redirectTarget.startsWith("/") && !redirectTarget.startsWith("//");
    router.push(isSafeInternalPath ? redirectTarget! : "/console");
  }

  async function handleSignIn(username: string, password: string) {
    setStatus("loading");
    setErrorMessage(null);
    try {
      await login(username, password);
      goToConsole();
    } catch (err) {
      setStatus("error");
      setErrorMessage(
        err instanceof ApiError && err.status === 401
          ? "Incorrect username or password."
          : "Sign in failed. Try again."
      );
    }
  }

  async function handleSignUp(username: string, password: string, role: SignupRole) {
    setStatus("loading");
    setErrorMessage(null);
    try {
      await signup(username, password, role);
      goToConsole();
    } catch (err) {
      setStatus("error");
      if (err instanceof ApiError && err.status === 409) {
        setErrorMessage("That username is already taken.");
      } else if (err instanceof ApiError && err.status === 400) {
        setErrorMessage("Password does not meet the minimum requirements.");
      } else if (err instanceof ApiError && err.status === 429) {
        setErrorMessage("Too many attempts. Wait a moment and try again.");
      } else {
        setErrorMessage("Could not create that account. Try again.");
      }
    }
  }

  function handleModeChange(nextMode: "signin" | "signup") {
    setMode(nextMode);
    setStatus("idle");
    setErrorMessage(null);
  }

  return (
    <LoginView
      mode={mode}
      onModeChange={handleModeChange}
      onSignIn={handleSignIn}
      onSignUp={handleSignUp}
      status={status}
      errorMessage={errorMessage}
    />
  );
}

export default function LoginPage() {
  useEffect(() => {
    document.title = "Stacks | Sign in";
  }, []);

  return (
    <Suspense
      fallback={
        <LoginView mode="signin" onModeChange={() => {}} onSignIn={() => {}} onSignUp={() => {}} status="idle" errorMessage={null} />
      }
    >
      <LoginForm />
    </Suspense>
  );
}
