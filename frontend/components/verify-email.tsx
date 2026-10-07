"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

export function VerifyEmail({ token }: { token: string | null }) {
  const [state, setState] = useState<"loading" | "success" | "error">(
    token ? "loading" : "error",
  );
  const [message, setMessage] = useState(
    token ? "Verifying your email address…" : "This verification link is missing its token.",
  );

  useEffect(() => {
    if (!token) return;
    let active = true;

    api<{ message: string }>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    }).then((result) => {
      if (active) {
        setState("success");
        setMessage(result.message);
      }
    }).catch((error: unknown) => {
      if (active) {
        setState("error");
        setMessage(error instanceof Error ? error.message : "Your email could not be verified.");
      }
    });

    return () => {
      active = false;
    };
  }, [token]);

  return (
    <main className="auth-page">
      <Link className="brand auth-brand" href="/"><i>W</i> WorkBit</Link>
      <Card className="auth-card" asChild><section aria-live="polite">
        <p className="eyebrow">EMAIL VERIFICATION</p>
        <h1>{state === "loading" ? "Verifying your email" : state === "success" ? "Email verified" : "Verification failed"}</h1>
        <Alert className={state === "error" ? "form-message error-state" : "form-message"} variant={state === "error" ? "destructive" : "default"} role={state === "error" ? "alert" : "status"}>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
        {state === "success" && <Button className="verify-login-link" asChild><Link href="/login">Continue to sign in</Link></Button>}
        {state === "error" && <p><Link href="/login">Return to sign in</Link></p>}
      </section></Card>
    </main>
  );
}
