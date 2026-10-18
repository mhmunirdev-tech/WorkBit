"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownToLine, ArrowLeft, ArrowRight, ArrowUpFromLine, Pause, Play } from "lucide-react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { formatUsd } from "../lib/utils";
import { Shell, ShellUser } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Skeleton } from "./ui/skeleton";

type Amount = string | number;

type DashboardBanner = {
  id: string;
  title: string;
  content: string;
  image_url: string;
  link_url: string | null;
};

type DashboardData = {
  available_balance: Amount;
  deposit_balance: Amount;
  earning_balance: Amount;
  package_active: boolean;
  package_purchase_status: string | null;
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
  return formatUsd(value);
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

function BannerCarousel({ banners }: { banners: DashboardBanner[] }) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [activePage, setActivePage] = useState(0);
  const [pageCount, setPageCount] = useState(1);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    function updatePageCount() {
      const element = viewportRef.current;
      if (!element) return;
      const maxScroll = element.scrollWidth - element.clientWidth;
      setPageCount(maxScroll > 1 ? Math.ceil(maxScroll / element.clientWidth) + 1 : 1);
    }

    updatePageCount();
    const observer = new ResizeObserver(updatePageCount);
    observer.observe(viewport);
    return () => observer.disconnect();
  }, [banners.length]);

  useEffect(() => {
    if (pageCount < 2 || paused) return;
    const timer = window.setInterval(() => {
      showPage((activePage + 1) % pageCount);
    }, 6000);
    return () => window.clearInterval(timer);
  }, [activePage, pageCount, paused]);

  if (banners.length === 0) return null;

  function showPage(page: number) {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const maxScroll = viewport.scrollWidth - viewport.clientWidth;
    viewport.scrollTo({
      left: pageCount > 1 ? (maxScroll * page) / (pageCount - 1) : 0,
      behavior: "smooth",
    });
    setActivePage(page);
  }

  function syncActivePage() {
    const viewport = viewportRef.current;
    if (!viewport || pageCount < 2) return;
    const maxScroll = viewport.scrollWidth - viewport.clientWidth;
    if (maxScroll <= 0) {
      setActivePage(0);
      return;
    }
    setActivePage(Math.round((viewport.scrollLeft / maxScroll) * (pageCount - 1)));
  }

  return (
    <section className="dashboard-banner-section" aria-label="WorkBit announcements">
      <div className="dashboard-banner-heading">
        <div><p className="eyebrow">WORKBIT UPDATES</p><h2>Announcements</h2></div>
        {pageCount > 1 && (
          <div className="dashboard-banner-controls" aria-label="Banner controls">
            <Button variant="ghost" size="icon" type="button" aria-label="Previous banners" onClick={() => showPage((activePage - 1 + pageCount) % pageCount)}>
              <ArrowLeft size={17} />
            </Button>
            <div className="dashboard-banner-dots" role="group" aria-label="Choose a banner group">
              {Array.from({ length: pageCount }, (_, index) => (
                <button
                  key={index}
                  className={`dashboard-banner-dot${index === activePage ? " is-active" : ""}`}
                  type="button"
                  aria-label={`Show banner group ${index + 1}`}
                  aria-pressed={index === activePage}
                  onClick={() => showPage(index)}
                />
              ))}
            </div>
            <Button variant="ghost" size="icon" type="button" aria-label="Next banners" onClick={() => showPage((activePage + 1) % pageCount)}>
              <ArrowRight size={17} />
            </Button>
            <Button variant="ghost" size="icon" type="button" aria-label={paused ? "Resume automatic banner rotation" : "Pause automatic banner rotation"} onClick={() => setPaused((value) => !value)}>
              {paused ? <Play size={15} /> : <Pause size={15} />}
            </Button>
          </div>
        )}
      </div>
      <div className="dashboard-banner-viewport" ref={viewportRef} onScroll={syncActivePage}>
        <div className="dashboard-banner-track">
          {banners.map((banner) => {
            const cardContent = (
              <>
                <img className="dashboard-banner-image" src={banner.image_url} alt="" />
                <div className="dashboard-banner-copy">
                  <h3>{banner.title}</h3>
                  {banner.content && <p>{banner.content}</p>}
                  {banner.link_url && <span className="dashboard-banner-card-link">Learn more <ArrowRight size={14} /></span>}
                </div>
              </>
            );
            return banner.link_url ? (
              <a className="dashboard-banner-card" href={banner.link_url} key={banner.id}>
                {cardContent}
              </a>
            ) : (
              <article className="dashboard-banner-card" key={banner.id}>{cardContent}</article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function EarningsChart({ points, currency }: { points: DashboardData["earnings_chart"]; currency: string }) {
  const [range, setRange] = useState(30);
  const today = new Date().toISOString().slice(0, 10);
  const rangeStart = new Date(`${today}T00:00:00.000Z`);
  rangeStart.setUTCDate(rangeStart.getUTCDate() - range + 1);
  const firstDate = rangeStart.toISOString().slice(0, 10);
  const visible = points.filter((point) => point.date >= firstDate && point.date <= today);
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
  const [referralMessage, setReferralMessage] = useState("");
  const [banners, setBanners] = useState<DashboardBanner[]>([]);
  const [bannerError, setBannerError] = useState("");

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

  useEffect(() => {
    let active = true;
    api<DashboardBanner[]>("/dashboard/banners")
      .then((result) => {
        if (active) setBanners(result);
      })
      .catch((reason: unknown) => {
        if (active) {
          setBannerError(reason instanceof Error ? reason.message : "Announcements could not be loaded.");
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
      const message = "Referral link copied.";
      setReferralMessage(message);
      showToast({ title: "Referral link copied", description: message, variant: "success" });
    } catch {
      const message = "Clipboard access is unavailable. Select and copy the referral link.";
      setReferralMessage(message);
      showToast({ title: "Could not copy link", description: message, variant: "destructive" });
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
        showToast({ title: "Referral link shared", description: "Your WorkBit referral link was shared.", variant: "success" });
      } catch (reason) {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        const message = "The referral link could not be shared from this device.";
        setReferralMessage(message);
        showToast({ title: "Could not share link", description: message, variant: "destructive" });
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
      <div className="dashboard-page">
        {banners.length > 0 && <BannerCarousel banners={banners} />}
        {bannerError && (
          <Alert className="state error-state" variant="destructive" role="alert">
            <AlertDescription>{bannerError}</AlertDescription>
          </Alert>
        )}

        <header className="dashboard-welcome">
          <div className="welcome-copy">
            <p className="eyebrow">{displayDate}</p>
            <h1>Welcome back, {firstName} <span aria-hidden="true">✦</span></h1>
            <p>Here’s your verified WorkBit activity at a glance.</p>
          </div>
          <div className="welcome-actions">
            {!data.package_active &&
              data.user.email_verified &&
              data.user.status === "ACTIVE" &&
              data.package_purchase_status !== "PENDING" && (
              <Button className="dashboard-cta deposit-cta" variant="outline" asChild>
                <Link href="/packages">
                  <ArrowDownToLine size={16} aria-hidden="true" />
                  Deposit
                </Link>
              </Button>
            )}
            <Button className="dashboard-cta withdraw-cta" asChild>
              <Link href="/withdraw">
                <ArrowUpFromLine size={16} aria-hidden="true" />
                Withdraw
              </Link>
            </Button>
          </div>
        </header>

        {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}

        <section className="dashboard-metrics" aria-label="Earnings and withdrawals">
          <Card className="dashboard-metric" asChild><article>
            <span className="metric-icon icon-green" aria-hidden="true">✧</span>
            <p>Earning balance</p>
            <h2>{money(data.earning_balance, data.currency)}</h2>
            <small>Available to withdraw or buy packages</small>
          </article></Card>
          <Card className="dashboard-metric" asChild><article>
            <span className="metric-icon icon-green" aria-hidden="true">✧</span>
            <p>Earned today</p>
            <h2>{money(data.stats.today_earnings, data.currency)}</h2>
            <small>Approved ledger credits</small>
          </article></Card>
          <Card className="dashboard-metric" asChild><article>
            <span className="metric-icon icon-violet" aria-hidden="true">✧</span>
            <p>Total earnings</p>
            <h2>{money(data.lifetime_earned, data.currency)}</h2>
            <small>Recorded by WorkBit</small>
          </article></Card>
          <Card className="dashboard-metric" asChild><article>
            <span className="metric-icon icon-slate" aria-hidden="true">↙</span>
            <p>Total withdrawn</p>
            <h2>{money(data.lifetime_withdrawn, data.currency)}</h2>
            <small>Completed wallet movements</small>
          </article></Card>
        </section>

        <section className="dashboard-community-grid" aria-label="Referral and verified earnings">
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
              <div><strong>{data.stats.active_referrals}</strong><span>Package members</span></div>
              <div><strong>{money(data.stats.referral_earnings, data.currency)}</strong><span>Earned</span></div>
            </div>
            <Button className="share-button" variant="secondary" type="button" onClick={shareReferralLink}>Share invite <span aria-hidden="true">↗</span></Button>
            {referralMessage && <Alert className="inline-status" role="status"><AlertDescription>{referralMessage}</AlertDescription></Alert>}
          </article></Card>
          <EarningsChart points={data.earnings_chart} currency={data.currency} />
        </section>

        <footer className="dashboard-footer">
          Offer completion and rewards depend on eligibility, provider confirmation, and WorkBit validation. Displayed rewards are not guaranteed payments.
        </footer>
      </div>
    </Shell>
  );
}
