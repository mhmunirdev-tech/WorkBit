"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../lib/api";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Checkbox } from "./ui/checkbox";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

export function AuthForm({ mode }: { mode: "login" | "register" | "forgot" }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [referralCode, setReferralCode] = useState("");

  useEffect(() => {
    if (mode === "register") {
      setReferralCode(new URLSearchParams(window.location.search).get("referral") ?? "");
    }
  }, [mode]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const data = new FormData(event.currentTarget);

    try {
      if (mode === "login") {
        await api("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: data.get("email"), password: data.get("password") }),
        });
        const requestedPath = new URLSearchParams(window.location.search).get("returnTo");
        const destination =
          requestedPath?.startsWith("/") && !requestedPath.startsWith("//")
            ? requestedPath
            : "/dashboard";
        window.location.assign(destination);
        return;
      }

      if (mode === "forgot") {
        const result = await api<{ message: string }>("/auth/forgot-password", {
          method: "POST",
          body: JSON.stringify({ email: data.get("email") }),
        });
        setMessage(result.message);
        return;
      }

      await api("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: data.get("fullName"),
          email: data.get("email"),
          password: data.get("password"),
          confirm_password: data.get("confirmPassword"),
          country: data.get("country"),
          referral_code: referralCode || null,
          terms_accepted: data.get("terms") === "on",
        }),
      });
      setMessage("Your account was created. Check your email to verify it.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The request could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  const title =
    mode === "login"
      ? "Welcome back"
      : mode === "register"
        ? "Create your account"
        : "Reset your password";

  return (
    <main className="auth-page">
      <Link className="brand auth-brand" href="/"><i>W</i> WorkBit</Link>
      <Card className="auth-card" asChild><section>
        <p className="eyebrow">{mode === "register" ? "GET STARTED" : "SECURE ACCESS"}</p>
        <h1>{title}</h1>
        <p>
          {mode === "forgot"
            ? "Enter your email and we’ll send a reset link if the account exists."
            : "Work. Complete. Earn — with transparent, verified rewards."}
        </p>
        <form onSubmit={submit}>
          {mode === "register" && (
            <>
              <Label>Full name<Input name="fullName" required minLength={2} /></Label>
              <Label>Country (ISO code)<Input name="country" required maxLength={2} placeholder="US" /></Label>
            </>
          )}
          <Label>Email<Input name="email" type="email" required /></Label>
          {mode !== "forgot" && (
            <Label>Password<Input name="password" type="password" required minLength={12} /></Label>
          )}
          {mode === "register" && (
            <>
              <Label>Confirm password<Input name="confirmPassword" type="password" required minLength={12} /></Label>
              <Label>
                Referral code (optional)
                <Input
                  name="referral"
                  value={referralCode}
                  onChange={(event) => setReferralCode(event.target.value)}
                />
              </Label>
              <Label className="check"><Checkbox name="terms" required /> I accept the Terms and Privacy Policy.</Label>
            </>
          )}
          <Button className="primary" disabled={busy}>
            {busy
              ? "Please wait…"
              : mode === "login"
                ? "Sign in"
                : mode === "register"
                  ? "Create account"
                  : "Send reset link"}
          </Button>
        </form>
        {message && <Alert className="form-message" role="status"><AlertDescription>{message}</AlertDescription></Alert>}
        {mode === "login" && <p><Link href="/forgot-password">Forgot password?</Link> · <Link href="/register">Create an account</Link></p>}
        {mode === "register" && <p>Already have an account? <Link href="/login">Sign in</Link></p>}
      </section></Card>
    </main>
  );
}
