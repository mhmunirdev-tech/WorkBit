"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowDownToLine, ArrowUpFromLine } from "lucide-react";
import { api } from "../lib/api";
import { Shell, ShellUser } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Skeleton } from "./ui/skeleton";

type Amount = string | number;

type DashboardData = {
  available_balance: Amount;
  pending_balance: Amount;
  lifetime_earned: Amount;
  lifetime_withdrawn: Amount;
  currency: string;
  user: ShellUser & {
    referral_url: string;
  };
  stats: {
    referrals: number;
    active_referrals: number;
    today_earnings: Amount;
    week_earnings: Amount;
    month_earnings: Amount;
    referral_earnings: Amount;
    pending_referral_earnings: Amount;
  };
  earnings_chart: Array<{ date: string; amount: Amount }>;
};

const ranges = [
  { label: "Today", days: 1 },
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
];

function money(value: Amount, currency: string) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function dateLabel(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function DashboardSkeleton() {
  return (
    <div className="dashboard-skeleton" aria-label="Loading dashboard data" aria-busy="true">
      <div className="skeleton-heading"><Skeleton className="h-5 w-1/3" /><Skeleton className="h-8 w-1/2" /></div>
      <div className="dashboard-metrics">
        {Array.from({ length: 6 }, (_, index) => (
          <Card className="dashboard-metric skeleton" key={index}>
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
          </Card>
        ))}
      </div>
      <div className="dashboard-loading-grid">
        <div className="panel skeleton"><div className="skeleton-bar" /><div className="skeleton-bar chart-skeleton" /></div>
        <div className="panel skeleton"><div className="skeleton-bar" /><div className="skeleton-bar chart-skeleton" /></div>
      </div>
    </div>
  );
}

function EarningsChart({ points, currency }: { points: DashboardData["earnings_chart"]; currency: string }) {
  const [range, setRange] = useState(30);
  const visible = points.slice(-range);
  const values = visible.map((point) => Number(point.amount));
  const maximum = Math.max(...values, 0);
  const coordinates = values.map((value, index) => ({
    x: visible.length < 2 ? 310 : 12 + (index / (visible.length - 1)) * 596,
    y: 158 - (maximum > 0 ? (value / maximum) * 136 : 0),
  }));
  const line = coordinates.map((point) => `${point.x},${point.y}`).join(" ");
  const area =
    coordinates.length > 0
      ? `M ${coordinates[0].x},160 L ${coordinates.map((point) => `${point.x},${point.y}`).join(" L ")} L ${coordinates.at(-1)?.x},160 Z`
      : "";
  const total = visible.reduce((sum, point) => sum + Number(point.amount), 0);

  return (
    <Card className="panel earnings-panel" asChild><section aria-labelledby="earnings-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">VERIFIED ACTIVITY</p>
          <h2 id="earnings-heading">Earnings overview</h2>
          <p className="panel-subtitle">Approved reward credits from your wallet ledger.</p>
        </div>
        <strong className="chart-total">{money(total, currency)}</strong>
      </div>
      <div className="range-tabs" role="group" aria-label="Earnings chart time range">
        {ranges.map((item) => (
          <Button
            variant={range === item.days ? "default" : "outline"}
            size="sm"
            type="button"
            className={range === item.days ? "selected" : ""}
            aria-pressed={range === item.days}
            key={item.days}
            onClick={() => setRange(item.days)}
          >
            {item.label}
          </Button>
        ))}
      </div>
      <svg
        className="earnings-chart"
        viewBox="0 0 620 180"
        role="img"
        aria-label={`Approved earnings for the last ${range} ${range === 1 ? "day" : "days"}. Total ${money(total, currency)}.`}
        preserveAspectRatio="none"
      >
        {[24, 68, 112, 160].map((y) => (
          <line key={y} x1="0" x2="620" y1={y} y2={y} className="chart-gridline" />
        ))}
        {area && <path d={area} className="chart-area-fill" />}
        {coordinates.length > 1 && <polyline points={line} className="chart-line" />}
        {coordinates.length === 1 && (
          <circle cx={coordinates[0].x} cy={coordinates[0].y} r="5" className="chart-point" />
        )}
      </svg>
      <div className="chart-dates" aria-hidden="true">
        <span>{visible[0] ? dateLabel(visible[0].date) : ""}</span>
        <span>{visible.at(-1) ? dateLabel(visible.at(-1)!.date) : ""}</span>
      </div>
      {total === 0 && (
        <p className="chart-empty-note">No approved rewards in this period. Pending rewards are shown separately.</p>
      )}
    </section></Card>
  );
}

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [depositNotice, setDepositNotice] = useState(false);
  const [referralMessage, setReferralMessage] = useState("");

  useEffect(() => {
    let active = true;
    api<DashboardData>("/dashboard")
      .then((result) => {
        if (!active) return;
        setData(result);
        setLoading(false);
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Your dashboard could not be loaded.");
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const displayDate = useMemo(
    () => new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(new Date()),
    [],
  );

  async function copyReferralLink() {
    if (!data) return;
    try {
      await navigator.clipboard.writeText(data.user.referral_url);
      setReferralMessage("Referral link copied.");
    } catch {
      setReferralMessage("Clipboard access is unavailable. Select and copy the referral link.");
    }
  }

  async function shareReferralLink() {
    if (!data) return;
    if (navigator.share) {
      try {
        await navigator.share({
          title: "Join me on WorkBit",
          text: "Explore verified earning offers on WorkBit.",
          url: data.user.referral_url,
        });
      } catch (reason) {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setReferralMessage("The referral link could not be shared from this device.");
      }
      return;
    }
    await copyReferralLink();
  }

  if (loading) {
    return <Shell><DashboardSkeleton /></Shell>;
  }

  if (!data) {
    return (
      <Shell>
        <section className="dashboard-fatal-error" role="alert">
          <p className="eyebrow">ACCOUNT OVERVIEW</p>
          <h1>Dashboard unavailable</h1>
          <p>{error || "Your account summary could not be loaded."}</p>
          <Button className="primary" onClick={() => window.location.reload()} type="button">Try again</Button>
        </section>
      </Shell>
    );
  }

  const firstName = data.user.full_name.trim().split(/\s+/)[0] || "there";

  return (
    <Shell user={data.user}>
      <header className="dashboard-welcome">
        <div className="welcome-copy">
          <p className="eyebrow">{displayDate}</p>
          <h1>Welcome back, {firstName} <span aria-hidden="true">✦</span></h1>
          <p>Here’s your verified WorkBit activity at a glance.</p>
          <Badge className={`account-status status-${data.user.status.toLowerCase()}`} variant="outline">
            <span className="status-dot" aria-hidden="true" />
            {data.user.status.replaceAll("_", " ")}
          </Badge>
        </div>
        <div className="welcome-actions">
          <Button
            className="dashboard-cta deposit-cta"
            variant="outline"
            type="button"
            onClick={() => setDepositNotice((visible) => !visible)}
            aria-expanded={depositNotice}
          >
            <ArrowDownToLine size={16} aria-hidden="true" />
            Deposit
          </Button>
          <Button className="dashboard-cta withdraw-cta" asChild>
            <Link href="/withdraw">
              <ArrowUpFromLine size={16} aria-hidden="true" />
              Withdraw
            </Link>
          </Button>
        </div>
      </header>

      {depositNotice && (
        <Alert className="deposit-notice" role="status">
          <AlertDescription>
            Deposits are not available yet. WorkBit does not have an approved bKash or Nagad merchant integration, so no amount can be charged or added.
          </AlertDescription>
        </Alert>
      )}

      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}

      <section className="dashboard-metrics" aria-label="Account balances and earnings">
        <Card className="dashboard-metric balance-metric" asChild><article>
          <span className="metric-icon icon-blue" aria-hidden="true">◈</span>
          <p>Available balance</p>
          <h2>{money(data.available_balance, data.currency)}</h2>
          <Link href="/wallet">Open wallet <span aria-hidden="true">→</span></Link>
        </article></Card>
        <Card className="dashboard-metric" asChild><article>
          <span className="metric-icon icon-amber" aria-hidden="true">◷</span>
          <p>Pending balance</p>
          <h2>{money(data.pending_balance, data.currency)}</h2>
          <small>Awaiting provider validation</small>
        </article></Card>
        <Card className="dashboard-metric" asChild><article>
          <span className="metric-icon icon-green" aria-hidden="true">✧</span>
          <p>Earned today</p>
          <h2>{money(data.stats.today_earnings, data.currency)}</h2>
          <small>Approved ledger credits</small>
        </article></Card>
        <Card className="dashboard-metric" asChild><article>
          <span className="metric-icon icon-green" aria-hidden="true">↗</span>
          <p>Earned this week</p>
          <h2>{money(data.stats.week_earnings, data.currency)}</h2>
          <small>Approved ledger credits</small>
        </article></Card>
        <Card className="dashboard-metric" asChild><article>
          <span className="metric-icon icon-blue" aria-hidden="true">◷</span>
          <p>Earned this month</p>
          <h2>{money(data.stats.month_earnings, data.currency)}</h2>
          <small>Approved ledger credits</small>
        </article></Card>
        <Card className="dashboard-metric" asChild><article>
          <span className="metric-icon icon-violet" aria-hidden="true">✧</span>
          <p>Lifetime earnings</p>
          <h2>{money(data.lifetime_earned, data.currency)}</h2>
          <small>Recorded by WorkBit</small>
        </article></Card>
        <Card className="dashboard-metric" asChild><article>
          <span className="metric-icon icon-green" aria-hidden="true">◎</span>
          <p>Referral earnings</p>
          <h2>{money(data.stats.referral_earnings, data.currency)}</h2>
          <small>{money(data.stats.pending_referral_earnings, data.currency)} pending</small>
        </article></Card>
        <Card className="dashboard-metric" asChild><article>
          <span className="metric-icon icon-slate" aria-hidden="true">↙</span>
          <p>Total withdrawn</p>
          <h2>{money(data.lifetime_withdrawn, data.currency)}</h2>
          <small>Completed wallet movements</small>
        </article></Card>
      </section>

      <section className="dashboard-primary-grid dashboard-one-column">
        <EarningsChart points={data.earnings_chart} currency={data.currency} />
      </section>

      <section className="dashboard-content-grid dashboard-one-column">
        <Card className="panel referral-panel" asChild><article>
          <div className="panel-heading">
            <div><p className="eyebrow">INVITE YOUR NETWORK</p><h2>Your referrals</h2></div>
            <span className="referral-emblem" aria-hidden="true">↗</span>
          </div>
          <p className="referral-description">Share your WorkBit invite link. Referral rewards are only shown after they are recorded in the wallet ledger.</p>
          <label className="referral-link-label" htmlFor="referral-link">Your referral link</label>
          <div className="referral-link-row">
            <Input id="referral-link" readOnly value={data.user.referral_url} onFocus={(event) => event.currentTarget.select()} />
            <Button className="secondary-button" variant="outline" type="button" onClick={copyReferralLink}>Copy</Button>
          </div>
          <div className="referral-stats">
            <div><strong>{data.stats.referrals}</strong><span>Total referrals</span></div>
            <div><strong>{data.stats.active_referrals}</strong><span>Active accounts</span></div>
            <div><strong>{money(data.stats.referral_earnings, data.currency)}</strong><span>Earned</span></div>
          </div>
          <Button className="share-button" variant="secondary" type="button" onClick={shareReferralLink}>Share invite <span aria-hidden="true">↗</span></Button>
          {referralMessage && <Alert className="inline-status" role="status"><AlertDescription>{referralMessage}</AlertDescription></Alert>}
        </article></Card>
      </section>

      <footer className="dashboard-footer">
        Offer completion and rewards depend on eligibility, provider confirmation, and WorkBit validation. Displayed rewards are not guaranteed payments.
      </footer>
    </Shell>
  );
}
