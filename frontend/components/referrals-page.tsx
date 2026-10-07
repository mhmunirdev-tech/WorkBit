"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Shell, ShellUser } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Skeleton } from "./ui/skeleton";

type ReferralsData = {
  currency: string;
  user: ShellUser & {
    referral_url: string;
  };
  stats: {
    referrals: number;
    active_referrals: number;
    referral_earnings: string | number;
    pending_referral_earnings: string | number;
  };
};

function formatMoney(value: string | number, currency: string) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function ReferralsPage() {
  const [data, setData] = useState<ReferralsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    api<ReferralsData>("/dashboard")
      .then((result) => {
        if (active) setData(result);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Referral information could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function copyReferralLink() {
    if (!data) return;
    try {
      await navigator.clipboard.writeText(data.user.referral_url);
      setMessage("Referral link copied.");
    } catch {
      setMessage("Clipboard access is unavailable. Select and copy the referral link.");
    }
  }

  return (
    <Shell user={data?.user}>
      <header className="top">
        <div>
          <p className="eyebrow">INVITE YOUR NETWORK</p>
          <h1>Referrals</h1>
          <p className="muted">Share your account's referral link and track attributed sign-ups.</p>
        </div>
      </header>
      {loading && (
        <Card className="panel" aria-busy="true" aria-label="Loading referral information">
          <Skeleton className="h-5 w-1/2" />
          <Skeleton className="h-4 w-1/3" />
        </Card>
      )}
      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      {data && (
        <Card className="panel referral-page-card">
          <div className="panel-heading">
            <div>
              <h2>Your referral link</h2>
              <p className="panel-subtitle">Referrals are attributed from the account registration record.</p>
            </div>
            <span className="referral-emblem" aria-hidden="true">↗</span>
          </div>
          <label className="referral-link-label" htmlFor="profile-referral-link">Invite URL</label>
          <div className="referral-link-row">
            <Input id="profile-referral-link" readOnly value={data.user.referral_url} onFocus={(event) => event.currentTarget.select()} />
            <Button className="secondary-button" variant="outline" type="button" onClick={copyReferralLink}>Copy link</Button>
          </div>
          <div className="referral-stats referral-page-stats">
            <div><strong>{data.stats.referrals}</strong><span>Total referrals</span></div>
            <div><strong>{data.stats.active_referrals}</strong><span>Active accounts</span></div>
            <div><strong>{formatMoney(data.stats.referral_earnings, data.currency)}</strong><span>Verified earnings</span></div>
          </div>
          <p className="muted">Pending referral earnings: {formatMoney(data.stats.pending_referral_earnings, data.currency)}</p>
          {message && <Alert className="inline-status" role="status"><AlertDescription>{message}</AlertDescription></Alert>}
          <p className="settings-limitation">No referral commission program is currently configured; verified referral earnings remain ledger-driven.</p>
        </Card>
      )}
    </Shell>
  );
}
