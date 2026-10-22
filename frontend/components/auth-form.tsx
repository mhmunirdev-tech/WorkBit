"use client";

import Link from "next/link";
import Image from "next/image";
import { FormEvent, useEffect, useState } from "react";
import { countries, type TCountryCode } from "countries-list";
import { ArrowRight, ChevronDown, LockKeyhole, Mail, ShieldCheck, Smartphone, UserRound, UsersRound, Zap } from "lucide-react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Checkbox } from "./ui/checkbox";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { PasswordInput } from "./ui/password-input";

const countryOptions = Object.entries(countries)
  .filter(([, country]) => country.phone.length > 0)
  .sort(([, first], [, second]) => first.name.localeCompare(second.name));

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
  const [showReferral, setShowReferral] = useState(false);
  const [selectedCountry, setSelectedCountry] = useState<TCountryCode>("BD");

  useEffect(() => {
    if (mode === "register") {
      const code = new URLSearchParams(window.location.search).get("referral") ?? "";
      setReferralCode(code);
      setShowReferral(Boolean(code));
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
    const data = new FormData(form);
    if (mode === "register" && data.get("password") !== data.get("confirmPassword")) {
      setMessage("Your passwords do not match.");
      return;
    }
    setBusy(true);
    setMessage("");

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
        const localPhone = String(data.get("phoneNumber") ?? "").replace(/\D/g, "").replace(/^0/, "");
        const countryData = countries[selectedCountry];
      await api("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: data.get("fullName"),
          email,
          password: data.get("password"),
          confirm_password: data.get("confirmPassword"),
          country: selectedCountry,
          phone_number: localPhone ? `+${countryData.phone[0]}${localPhone}` : null,
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
    <main className={`auth-page auth-page-${mode}`}>
      <div className="auth-layout">
        <aside className="auth-showcase" aria-label="WorkBit welcome">
          <Link className="brand auth-showcase-brand" href="/"><i>W</i> WorkBit</Link>
          <div className="auth-hero-art">
            <Image
              src="/images/auth-background.png"
              alt="A WorkBit member working at a laptop, with secure account and community symbols"
              width={1536}
              height={1024}
              priority
              unoptimized
              sizes="(max-width: 700px) 100vw, 50vw"
            />
          </div>
          <div className="auth-showcase-copy">
            <span className="auth-showcase-mark">WORK SMARTER</span>
            <h2>Your journey <span>begins here.</span></h2>
            <p>Make your ideas a reality with a community built around progress and rewards.</p>
          </div>
          <div className="auth-benefits">
            <div><Zap aria-hidden="true" /><span><strong>Fast &amp; Easy</strong><small>Get started in minutes</small></span></div>
            <div><ShieldCheck aria-hidden="true" /><span><strong>Secure</strong><small>Your data is safe</small></span></div>
            <div><UsersRound aria-hidden="true" /><span><strong>Grow Together</strong><small>Build your future</small></span></div>
          </div>
        </aside>
        <Card className="auth-card auth-form-panel" asChild><section>
        <Link className="auth-brand-badge" href="/"><i>W</i><span>WorkBit</span></Link>
        <h1>{title}</h1>
        <p className="auth-subtitle">
          {mode === "forgot"
            ? "Enter your email and we’ll send a reset link if the account exists."
            : mode === "register"
              ? "Work. Connect. Earn — with transparent, verified rewards."
              : "Work. Connect. Earn — with transparent, verified rewards."}
        </p>
        <form className="auth-form" onSubmit={submit} noValidate>
          {mode === "register" && (
            <>
              <Label className="auth-field">
                Full name
                <span className="auth-input-shell">
                  <UserRound aria-hidden="true" />
                  <Input name="fullName" autoComplete="name" required minLength={2} placeholder="Your full name" />
                </span>
              </Label>
              <Label className="auth-field">
                Country
                <select
                  className="auth-country-select"
                  value={selectedCountry}
                  onChange={(event) => setSelectedCountry(event.target.value as TCountryCode)}
                  required
                  aria-label="Country"
                >
                  {countryOptions.map(([code, country]) => (
                    <option key={code} value={code}>
                      {country.name} ({code}) +{country.phone[0]}
                    </option>
                  ))}
                </select>
                <input type="hidden" name="country" value={selectedCountry} />
              </Label>
              <Label className="auth-field">
                Mobile number
                <span className="auth-phone-control">
                  <span className="auth-phone-prefix" aria-label={`Calling code +${countries[selectedCountry].phone[0]}`}>
                    +{countries[selectedCountry].phone[0]}
                  </span>
                  <Smartphone aria-hidden="true" />
                  <Input
                    name="phoneNumber"
                    type="tel"
                    inputMode="tel"
                    autoComplete="tel-national"
                    placeholder="1 555 123 4567"
                    maxLength={18}
                    required
                  />
                </span>
              </Label>
            </>
          )}
          <Label className="auth-field">
            Email address
            <span className="auth-input-shell">
              <Mail aria-hidden="true" />
              <Input name="email" type="email" autoComplete="email" required placeholder="you@example.com" />
            </span>
          </Label>
          {mode !== "forgot" && (
            <Label className="auth-field">
              Password
              <span className="auth-input-shell">
                <LockKeyhole aria-hidden="true" />
                <PasswordInput name="password" autoComplete={mode === "register" ? "new-password" : "current-password"} required minLength={12} placeholder="At least 12 characters" />
              </span>
            </Label>
          )}
          {mode === "register" && (
            <>
              <Label className="auth-field">
                Confirm password
                <span className="auth-input-shell">
                  <LockKeyhole aria-hidden="true" />
                  <PasswordInput name="confirmPassword" autoComplete="new-password" required minLength={12} placeholder="Re-enter your password" />
                </span>
              </Label>
              <input type="hidden" name="referral" value={referralCode} />
              <button
                className="auth-referral-toggle"
                type="button"
                aria-expanded={showReferral}
                onClick={() => setShowReferral((shown) => !shown)}
              >
                Have a referral code? <ChevronDown aria-hidden="true" />
              </button>
              {showReferral && (
                <Label className="auth-field">
                  Referral code
                  <Input
                    name="referralVisible"
                    value={referralCode}
                    onChange={(event) => setReferralCode(event.target.value)}
                    autoComplete="off"
                    placeholder="Enter code"
                  />
                </Label>
              )}
              <Label className="check policy-acceptance">
                <Checkbox name="terms" required />
                <span>
                  I accept the <Link href="/terms">Terms of Service</Link> and <Link href="/privacy">Privacy Policy</Link>.
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
            {mode === "register" && !busy && <ArrowRight aria-hidden="true" />}
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
      </div>
    </main>
  );
}
