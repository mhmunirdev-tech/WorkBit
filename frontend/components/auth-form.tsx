"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Checkbox } from "./ui/checkbox";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { PasswordInput } from "./ui/password-input";

export function AuthForm({
  mode,
  defaultDestination = "/dashboard",
}: {
  mode: "login" | "register" | "forgot";
  defaultDestination?: string;
}) {
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
    const form = event.currentTarget;
    if (!form.checkValidity()) {
      const invalidField = form.querySelector(":invalid");
      const message = invalidField instanceof HTMLInputElement && invalidField.type === "email"
        ? "Enter a valid email address."
        : invalidField instanceof HTMLInputElement && invalidField.type === "password"
          ? "Check the password and make sure it meets the minimum length."
          : "Please complete all required fields with valid information.";
      setMessage(message);
      if (mode === "login") {
        showToast({
          title: "Check your sign-in details",
          description: message,
          variant: "destructive",
          kind: "login-error",
        });
      }
      return;
    }
    setBusy(true);
    setMessage("");
    const data = new FormData(event.currentTarget);

    try {
      if (mode === "login") {
        const loginPath = defaultDestination === "/admin" ? "/auth/admin/login" : "/auth/login";
        await api(loginPath, {
          method: "POST",
          body: JSON.stringify({ email: data.get("email"), password: data.get("password") }),
        });
        const requestedPath = new URLSearchParams(window.location.search).get("returnTo");
        const requestedPathname = requestedPath?.split("?")[0].replace(/\/+$/, "") || "";
        const isAdminLogin = defaultDestination === "/admin";
        const safeRequestedPath = isAdminLogin
          ? requestedPathname === "/admin" || requestedPathname.startsWith("/admin/")
            ? requestedPathname === "/admin/login" ? null : requestedPath
            : null
          : requestedPathname === "/login" || requestedPathname === "/admin/login"
            ? null
            : requestedPath;
        const destination =
          safeRequestedPath?.startsWith("/") && !safeRequestedPath.startsWith("//")
            ? safeRequestedPath
            : defaultDestination;
        showToast({
          title: "Signed in",
          description: "Welcome back to WorkBit.",
          variant: "success",
          kind: "login-success",
        });
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

      const email = String(data.get("email") ?? "").trim();
      await api("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: data.get("fullName"),
          email,
          password: data.get("password"),
          confirm_password: data.get("confirmPassword"),
          country: data.get("country"),
          referral_code: referralCode || null,
          terms_accepted: data.get("terms") === "on",
        }),
      });
      showToast({
        title: "Verification code sent",
        description: "Your account is ready. Check your email for the verification code.",
        variant: "success",
        kind: "otp-sent",
      });
      window.location.assign(`/verify-email?email=${encodeURIComponent(email)}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "The request could not be completed.";
      setMessage(message);
      if (mode === "login") {
        showToast({
          title: "Sign-in failed",
          description: message,
          variant: "destructive",
          kind: "login-error",
        });
      }
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
        <form onSubmit={submit} noValidate>
          {mode === "register" && (
            <>
              <Label>Full name<Input name="fullName" required minLength={2} /></Label>
              <Label>Country (ISO code)<Input name="country" required maxLength={2} placeholder="US" /></Label>
            </>
          )}
          <Label>Email<Input name="email" type="email" required /></Label>
          {mode !== "forgot" && (
            <Label>Password<PasswordInput name="password" required minLength={12} /></Label>
          )}
          {mode === "register" && (
            <>
              <Label>Confirm password<PasswordInput name="confirmPassword" required minLength={12} /></Label>
              <Label>
                Referral code (optional)
                <Input
                  name="referral"
                  value={referralCode}
                  onChange={(event) => setReferralCode(event.target.value)}
                />
              </Label>
              <Label className="check policy-acceptance">
                <Checkbox name="terms" required />
                <span>
                  I accept the <Link href="/terms">Terms of Service</Link> and{" "}
                  <Link href="/privacy">Privacy Policy</Link>.
                </span>
              </Label>
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
        {mode === "login" && (
          defaultDestination === "/admin"
            ? <p><Link href="/forgot-password">Forgot password?</Link> · Admin accounts are provisioned by an authorized administrator. <Link href="/login">User sign in</Link></p>
            : <p><Link href="/forgot-password">Forgot password?</Link> · <Link href="/register">Create an account</Link></p>
        )}
        {mode === "register" && <p>Already have an account? <Link href="/login">Sign in</Link></p>}
      </section></Card>
    </main>
  );
}
