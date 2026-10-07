"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Shell, ShellUser } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Avatar, AvatarFallback } from "./ui/avatar";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Skeleton } from "./ui/skeleton";

type AccountData = {
  currency: string;
  user: ShellUser & {
    email: string;
    country: string;
    created_at: string;
    referral_code: string;
    referral_url: string;
  };
  stats: {
    referrals: number;
    active_referrals: number;
    referral_earnings: string | number;
    pending_referral_earnings: string | number;
  };
};

function useAccount() {
  const [account, setAccount] = useState<AccountData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api<AccountData>("/dashboard")
      .then((result) => {
        if (active) setAccount(result);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Account information could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { account, loading, error };
}

function AccountState({ loading, error }: { loading: boolean; error: string }) {
  if (loading) {
    return (
      <Card className="panel" aria-busy="true" aria-label="Loading account information">
        <Skeleton className="h-5 w-1/2" />
        <Skeleton className="h-4 w-1/3" />
      </Card>
    );
  }
  if (error) return <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>;
  return null;
}

function formatMoney(value: string | number, currency: string) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function ProfilePage() {
  const { account, loading, error } = useAccount();

  return (
    <Shell user={account?.user}>
      <header className="top">
        <div>
          <p className="eyebrow">ACCOUNT</p>
          <h1>Your profile</h1>
          <p className="muted">Review the account details WorkBit currently has on file.</p>
        </div>
      </header>
      <AccountState loading={loading} error={error} />
      {account && (
        <Card className="panel account-profile-card">
          <div className="profile-identity">
            <Avatar className="account-panel-avatar" aria-hidden="true"><AvatarFallback>{account.user.full_name.slice(0, 1).toUpperCase()}</AvatarFallback></Avatar>
            <div><h2>{account.user.full_name}</h2><p>{account.user.email}</p></div>
          </div>
          <dl className="account-details">
            <div><dt>Account status</dt><dd>{account.user.status.replaceAll("_", " ")}</dd></div>
            <div><dt>Email verification</dt><dd className={account.user.email_verified ? "good-status" : "attention-status"}>{account.user.email_verified ? "Verified" : "Not verified"}</dd></div>
            <div><dt>Country</dt><dd>{account.user.country}</dd></div>
            <div><dt>Member since</dt><dd>{new Date(account.user.created_at).toLocaleDateString()}</dd></div>
            <div><dt>Referral code</dt><dd>{account.user.referral_code}</dd></div>
          </dl>
          <p className="muted">Profile fields are read-only because profile editing is not available in the current account API.</p>
          <Button className="text-link" variant="link" asChild><Link href="/settings">Account settings →</Link></Button>
        </Card>
      )}
    </Shell>
  );
}

export function SettingsPage() {
  const { account, loading, error } = useAccount();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function resendVerification() {
    setBusy(true);
    setMessage("");
    try {
      const result = await api<{ message: string }>("/auth/resend-verification", { method: "POST" });
      setMessage(result.message);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "The verification request could not be sent.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell user={account?.user}>
      <header className="top">
        <div>
          <p className="eyebrow">PREFERENCES & SECURITY</p>
          <h1>Account settings</h1>
          <p className="muted">Manage the security actions currently supported for your account.</p>
        </div>
      </header>
      <AccountState loading={loading} error={error} />
      {account && (
        <Card className="panel settings-card">
          <div className="panel-heading">
            <div>
              <h2>Email verification</h2>
              <p className="panel-subtitle">A verified email helps protect access to your WorkBit account.</p>
            </div>
            <Badge className={`settings-status ${account.user.email_verified ? "is-good" : "needs-action"}`} variant="outline">
              {account.user.email_verified ? "Verified" : "Not verified"}
            </Badge>
          </div>
          <p className="settings-email">{account.user.email}</p>
          {!account.user.email_verified && (
            <Button className="primary" type="button" onClick={resendVerification} disabled={busy}>
              {busy ? "Requesting…" : "Resend verification email"}
            </Button>
          )}
          {message && <Alert className="inline-status" role="status"><AlertDescription>{message}</AlertDescription></Alert>}
          <div className="settings-divider" />
          <h2>Password</h2>
          <p className="panel-subtitle">Password recovery is available through the secure reset flow.</p>
          <Button className="text-link" variant="link" asChild><Link href="/forgot-password">Reset your password →</Link></Button>
          <p className="muted settings-limitation">Other preferences and session management are not exposed by the current account API.</p>
        </Card>
      )}
    </Shell>
  );
}
