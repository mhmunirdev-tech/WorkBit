"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api } from "../lib/api";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

export function VerifyEmail({ email: initialEmail }: { email: string }) {
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [state, setState] = useState<"pending" | "success">("pending");
  const [message, setMessage] = useState("");

  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const result = await api<{ message: string }>("/auth/verify-email", {
        method: "POST",
        body: JSON.stringify({ email, code }),
      });
      setState("success");
      setMessage(result.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Your email could not be verified.");
    } finally {
      setBusy(false);
    }
  }

  async function resendCode() {
    if (!email.trim()) {
      setMessage("Enter the email address you used to create your account.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const result = await api<{ message: string }>("/auth/request-verification", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setMessage(result.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "A new verification code could not be requested.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <Link className="brand auth-brand" href="/"><i>W</i> WorkBit</Link>
      <Card className="auth-card" asChild><section aria-live="polite">
        <p className="eyebrow">EMAIL VERIFICATION</p>
        <h1>{state === "success" ? "Email verified" : "Enter your verification code"}</h1>
        <p>
          {state === "success"
            ? "Your email address is verified. You can now sign in."
            : "Enter the six-digit code we sent to your email address. The code expires after 10 minutes."}
        </p>
        {state === "pending" && (
          <form onSubmit={(event) => void verify(event)}>
            <Label>
              Email address
              <Input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </Label>
            <Label>
              Six-digit code
              <Input
                name="code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                minLength={6}
                maxLength={6}
                required
                value={code}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="000000"
                className="verification-code-input"
              />
            </Label>
            <Button className="primary" disabled={busy || code.length !== 6}>
              {busy ? "Please wait…" : "Verify email"}
            </Button>
          </form>
        )}
        {message && (
          <Alert className="form-message" role={state === "success" ? "status" : "alert"}>
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}
        {state === "pending" ? (
          <Button className="text-link" variant="link" type="button" onClick={() => void resendCode()} disabled={busy}>
            Resend verification code
          </Button>
        ) : (
          <Button className="verify-login-link" asChild><Link href="/login">Continue to sign in</Link></Button>
        )}
        <p><Link href="/login">Return to sign in</Link></p>
      </section></Card>
    </main>
  );
}
