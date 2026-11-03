"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api } from "../lib/api";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

export function FraudAppealForm() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [statement, setStatement] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function requestCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const result = await api<{ message: string }>("/fraud/appeals/request-code", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setMessage(result.message);
      setCodeSent(true);
    } catch (failure) {
      setMessage(failure instanceof Error ? failure.message : "The request could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitAppeal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const result = await api<{ message: string }>("/fraud/appeals", {
        method: "POST",
        body: JSON.stringify({ email, code, statement }),
      });
      setMessage(result.message);
      setSubmitted(true);
    } catch (failure) {
      setMessage(failure instanceof Error ? failure.message : "Your appeal could not be submitted.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page auth-page-login">
      <Card className="auth-card fraud-appeal-card">
        <Link className="auth-brand-badge" href="/"><i>W</i><span>WorkBit</span></Link>
        <h1>Request an account review</h1>
        <p className="auth-subtitle">If your account is restricted, request a manual review using its verified email address.</p>
        <form className="auth-form" onSubmit={codeSent ? submitAppeal : requestCode}>
          <Label className="auth-field">
            Account email address
            <Input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={codeSent}
              placeholder="you@example.com"
            />
          </Label>
          {codeSent && !submitted && (
            <>
              <Label className="auth-field">
                Email verification code
                <Input
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  required
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  placeholder="6-digit code"
                />
              </Label>
              <Label className="auth-field">
                Explain why you are requesting a review
                <textarea
                  required
                  minLength={20}
                  maxLength={1000}
                  value={statement}
                  onChange={(event) => setStatement(event.target.value)}
                  placeholder="Provide relevant details for the review."
                />
              </Label>
            </>
          )}
          {!submitted && <Button className="primary" disabled={busy}>
            {busy ? "Please wait…" : codeSent ? "Submit appeal" : "Request verification code"}
          </Button>}
        </form>
        {message && <Alert className="form-message" role="status"><AlertDescription>{message}</AlertDescription></Alert>}
        {submitted && <p>Your appeal is queued for manual review. Account access is not restored automatically.</p>}
        <p><Link href="/login">Return to sign in</Link></p>
      </Card>
    </main>
  );
}
