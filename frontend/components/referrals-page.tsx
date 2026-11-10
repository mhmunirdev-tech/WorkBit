"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Copy, Share2, UsersRound } from "lucide-react";
import Link from "next/link";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { formatUsd, formatWbcFromUsd } from "../lib/utils";
import { Shell, ShellUser } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Skeleton } from "./ui/skeleton";

type ReferralData = {
  currency: string;
  withdrawal_summary: { usd_bdt_rate: number | string | null };
  user: ShellUser & { referral_url: string };
  stats: {
    referrals: number;
    active_referrals: number;
    referral_earnings: number | string;
    pending_referral_earnings: number | string;
  };
};

function referralAmount(amount: number | string, rate: number | string | null) {
  return formatWbcFromUsd(amount, rate) ?? formatUsd(amount);
}

export function ReferralsPage() {
  const [data, setData] = useState<ReferralData | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    api<ReferralData>("/dashboard")
      .then((result) => { if (active) setData(result); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Referral information could not be loaded.");
      });
    return () => { active = false; };
  }, []);

  async function copyLink() {
    if (!data) return;
    try {
      await navigator.clipboard.writeText(data.user.referral_url);
      setCopied(true);
      showToast({ title: "Referral link copied", description: "Share it with someone who may be interested in WorkBit.", variant: "success" });
    } catch {
      showToast({ title: "Could not copy link", description: "Select the link and copy it manually.", variant: "destructive" });
    }
  }

  async function shareLink() {
    if (!data) return;
    if (!navigator.share) {
      await copyLink();
      return;
    }
    try {
      await navigator.share({
        title: "Join me on WorkBit",
        text: "Explore provider-verified offers on WorkBit. No package purchase is required to start.",
        url: data.user.referral_url,
      });
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        showToast({ title: "Could not share link", description: "Try copying the referral link instead.", variant: "destructive" });
      }
    }
  }

  return (
    <Shell user={data?.user}>
      <header className="top">
        <div><p className="eyebrow">INVITE YOUR NETWORK</p><h1>Referrals</h1><p className="muted">Share your link and see how referral rewards work.</p></div>
        <Button variant="outline" asChild><Link href="/dashboard"><ArrowLeft size={15} /> Dashboard</Link></Button>
      </header>
      {error && <Alert className="state error-state" variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {!data ? (
        <Card className="panel"><Skeleton className="h-6 w-1/3" /><Skeleton className="mt-4 h-10 w-full" /></Card>
      ) : (
        <div className="referrals-page-grid">
          <Card className="panel referral-share-panel">
            <span className="referrals-icon"><UsersRound size={22} /></span>
            <h2>Invite someone to WorkBit</h2>
            <p>They can create an account and explore eligible offers without buying an earning package.</p>
            <label className="referral-link-label" htmlFor="dedicated-referral-link">Your referral link</label>
            <div className="referral-link-row">
              <Input id="dedicated-referral-link" readOnly value={data.user.referral_url} onFocus={(event) => event.currentTarget.select()} />
              <Button type="button" variant="outline" onClick={() => void copyLink()}><Copy size={15} /> {copied ? "Copied" : "Copy"}</Button>
            </div>
            <Button className="share-button" type="button" onClick={() => void shareLink()}><Share2 size={16} /> Share invite</Button>
          </Card>
          <Card className="panel">
            <p className="eyebrow">REFERRAL REWARDS</p>
            <h2>Clear reward conditions</h2>
            <p>Referral commissions are based on a referred member’s approved package payments—not offer completions.</p>
            <ul className="referral-terms-list">
              <li><strong>20%</strong><span>of the first package payment after admin approval</span></li>
              <li><strong>5%</strong><span>of each later package payment after admin approval</span></li>
            </ul>
            <p className="muted">Package purchase is optional for earning from eligible offers. Referral commissions appear in your wallet ledger after approval.</p>
          </Card>
          <section className="referral-stats referrals-page-stats" aria-label="Referral summary">
            <Card className="dashboard-metric"><article><p>Total referrals</p><h2>{data.stats.referrals}</h2><small>Accounts using your invite link</small></article></Card>
            <Card className="dashboard-metric"><article><p>Package members</p><h2>{data.stats.active_referrals}</h2><small>Active referred members with an approved package</small></article></Card>
            <Card className="dashboard-metric"><article><p>Referral income</p><h2>{referralAmount(data.stats.referral_earnings, data.withdrawal_summary.usd_bdt_rate)}</h2><small>Approved wallet credits</small></article></Card>
            <Card className="dashboard-metric"><article><p>Pending referral income</p><h2>{referralAmount(data.stats.pending_referral_earnings, data.withdrawal_summary.usd_bdt_rate)}</h2><small>Awaiting approval, if any</small></article></Card>
          </section>
        </div>
      )}
    </Shell>
  );
}
