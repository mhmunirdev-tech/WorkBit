"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight, BadgeCheck, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";
import { Alert, AlertDescription } from "./ui/alert";
import { Card } from "./ui/card";

type TrustStats = {
  registered_users: number;
  total_payouts_bdt: number | string;
  paid_withdrawal_count: number;
  offer_approval_rate: number | string | null;
};

function bdt(value: number | string) {
  return new Intl.NumberFormat("en-BD", {
    style: "currency",
    currency: "BDT",
    maximumFractionDigits: 0,
  }).format(Number(value));
}

export function TrustCenter() {
  const [stats, setStats] = useState<TrustStats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api<TrustStats>("/public/stats")
      .then((result) => { if (active) setStats(result); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Public trust information is unavailable.");
      });
    return () => { active = false; };
  }, []);

  return (
    <main className="trust-center-page">
      <header className="landing-nav">
        <Link className="brand landing-brand" href="/" aria-label="WorkBit home"><i>W</i><span>WorkBit</span></Link>
        <nav aria-label="Main navigation"><Link href="/offers">Offers</Link><Link href="/trust" aria-current="page">Trust center</Link><Link href="/withdrawal-policy">Withdrawal policy</Link></nav>
        <div className="nav-actions"><Link href="/login">Log in</Link><Link className="trust-create-link" href="/register">Get started <ArrowUpRight size={15} /></Link></div>
      </header>
      <section className="trust-hero">
        <span className="eyebrow"><ShieldCheck size={15} /> WORKBIT TRUST CENTER</span>
        <h1>Know what happens to your rewards.</h1>
        <p>Offers are subject to provider eligibility and verification. We show reward and payout status clearly, and never promise earnings.</p>
      </section>
      {error && <Alert className="state error-state" variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      <section className="trust-stats" aria-label="Privacy-safe platform totals">
        <Card><span>Paid out (lifetime)</span><strong>{stats ? bdt(stats.total_payouts_bdt) : "—"}</strong><small>Based on completed payout records</small></Card>
        <Card><span>Completed withdrawals</span><strong>{stats ? stats.paid_withdrawal_count.toLocaleString() : "—"}</strong><small>Aggregate count; no personal payout details are public</small></Card>
        <Card><span>Registered users</span><strong>{stats ? stats.registered_users.toLocaleString() : "—"}</strong><small>Aggregate account count</small></Card>
      </section>
      <section className="trust-information">
        <Card>
          <BadgeCheck size={21} />
          <h2>How rewards are verified</h2>
          <p>Providers report conversions to WorkBit. We validate each callback and apply the configured reward policy before crediting pending or available wallet balance.</p>
          <Link href="/reward-policy">Read the reward policy <ArrowUpRight size={14} /></Link>
        </Card>
        <Card>
          <ShieldCheck size={21} />
          <h2>How withdrawals work</h2>
          <p>Eligible requests reserve withdrawable earnings and are reviewed manually. The wallet shows request status; processing time can vary and no fixed timeline is promised.</p>
          <Link href="/withdrawal-policy">Read the withdrawal policy <ArrowUpRight size={14} /></Link>
        </Card>
        <Card>
          <ShieldCheck size={21} />
          <h2>Your privacy</h2>
          <p>Public payout figures are aggregated. We do not publish payout recipients, account numbers, or individual transaction references.</p>
          <Link href="/privacy">Read the privacy policy <ArrowUpRight size={14} /></Link>
        </Card>
      </section>
      <footer className="trust-footer">
        <p>Offer availability varies by country, device, and provider. Package purchase is optional for eligible offer activity.</p>
        <Link href="/support">Need help? Contact support</Link>
      </footer>
    </main>
  );
}
