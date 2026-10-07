"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api } from "../lib/api";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

export function ResetPassword({ token }: { token: string | null }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(
    token ? "" : "This password reset link is missing its token.",
  );
  const [success, setSuccess] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;

    const data = new FormData(event.currentTarget);
    const password = String(data.get("password") ?? "");
    const confirmPassword = String(data.get("confirmPassword") ?? "");
    if (password !== confirmPassword) {
      setMessage("The passwords do not match.");
      setSuccess(false);
      return;
    }

    setBusy(true);
    setMessage("");
    try {
      const result = await api<{ message: string }>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, password, confirm_password: confirmPassword }),
      });
      setMessage(result.message);
      setSuccess(true);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Your password could not be reset.");
      setSuccess(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <Link className="brand auth-brand" href="/"><i>W</i> WorkBit</Link>
      <Card className="auth-card" asChild><section>
        <p className="eyebrow">ACCOUNT SECURITY</p>
        <h1>Reset your password</h1>
        {success ? (
          <>
            <Alert className="form-message" role="status"><AlertDescription>{message}</AlertDescription></Alert>
            <Link href="/login">Continue to sign in</Link>
          </>
        ) : (
          <>
            {token ? (
              <form onSubmit={submit}>
                <Label>
                  New password
                  <Input name="password" type="password" minLength={12} maxLength={128} required autoComplete="new-password" />
                </Label>
                <Label>
                  Confirm new password
                  <Input name="confirmPassword" type="password" minLength={12} maxLength={128} required autoComplete="new-password" />
                </Label>
                <Button className="primary" type="submit" disabled={busy}>
                  {busy ? "Updating…" : "Update password"}
                </Button>
              </form>
            ) : (
              <Alert className="form-message error-state" variant="destructive"><AlertDescription>{message}</AlertDescription></Alert>
            )}
            {token && message && <Alert className="form-message error-state" variant="destructive"><AlertDescription>{message}</AlertDescription></Alert>}
            <p><Link href="/login">Return to sign in</Link></p>
          </>
        )}
      </section></Card>
    </main>
  );
}
