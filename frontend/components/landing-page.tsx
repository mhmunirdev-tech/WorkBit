"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight, BadgeCheck, Check, ClipboardList, Clock3, Gamepad2, PackageCheck, ShieldCheck, Smartphone, Sparkles, UsersRound, WalletCards } from "lucide-react";
import { api } from "../lib/api";
import { formatUsd } from "../lib/utils";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "./ui/accordion";
import { Skeleton } from "./ui/skeleton";

type Offer = {
  id: string;
  title: string;
  short_description: string;
  category: string;
  user_reward: string;
  currency: string;
  estimated_time_minutes: number;
  is_demo: boolean;
};

type PublicStats = {
  registered_users: number;
  total_payouts_bdt: number | string;
  active_packages: number;
  offer_approval_rate: number | string | null;
};

type EarningPackage = {
  code: string;
  name: string;
  description: string;
  amount: number | string;
  currency: string;
  duration_days: number;
};

const publicStatItems = [
  {
    key: "registered_users",
    label: "Registered users",
    icon: UsersRound,
    tone: "mint",
  },
  {
    key: "total_payouts_bdt",
    label: "Paid out",
    icon: WalletCards,
    tone: "navy",
  },
  {
    key: "active_packages",
    label: "Active packages",
    icon: PackageCheck,
    tone: "teal",
  },
  {
    key: "offer_approval_rate",
    label: "Offer approval rate",
    icon: BadgeCheck,
    tone: "green",
  },
] as const;

function formatCompactNumber(value: number, maximumFractionDigits = 1): string {
  return new Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumFractionDigits,
  }).format(value);
}

const steps = [
  ["01", "Choose an offer", "Explore opportunities available for your country and device."],
  ["02", "Complete the task", "Follow the offer requirements and complete the activity."],
  ["03", "Get verified", "The provider confirms the conversion before WorkBit records a reward."],
  ["04", "Track your reward", "See pending and available amounts in your account ledger."],
];

export function LandingPage() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [offerError, setOfferError] = useState("");
  const [publicStats, setPublicStats] = useState<PublicStats | null>(null);
  const [statsError, setStatsError] = useState("");
  const [packages, setPackages] = useState<EarningPackage[]>([]);
  const [packagesLoading, setPackagesLoading] = useState(true);
  const [packagesError, setPackagesError] = useState("");

  useEffect(() => {
    let active = true;
    api<Offer[]>("/offers?limit=3")
      .then((result) => { if (active) setOffers(result); })
      .catch((error: unknown) => {
        if (active) setOfferError(error instanceof Error ? error.message : "Offers are temporarily unavailable.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    api<EarningPackage[]>("/public/packages")
      .then((result) => { if (active) setPackages(result); })
      .catch((error: unknown) => {
        if (active) {
          setPackagesError(error instanceof Error ? error.message : "Package information is temporarily unavailable.");
        }
      })
      .finally(() => { if (active) setPackagesLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    api<PublicStats>("/public/stats")
      .then((result) => { if (active) setPublicStats(result); })
      .catch((error: unknown) => {
        if (active) {
          setStatsError(error instanceof Error ? error.message : "Platform statistics are temporarily unavailable.");
        }
      });
    return () => { active = false; };
  }, []);

  function formatStat(key: (typeof publicStatItems)[number]["key"]): string {
    if (!publicStats) return "—";
    if (key === "registered_users") {
      return formatCompactNumber(publicStats.registered_users);
    }
    if (key === "total_payouts_bdt") {
      return `$${formatCompactNumber(Number(publicStats.total_payouts_bdt))}`;
    }
    if (key === "active_packages") {
      return new Intl.NumberFormat().format(publicStats.active_packages);
    }
    if (publicStats.offer_approval_rate === null) return "—";
    return `${formatCompactNumber(Number(publicStats.offer_approval_rate))}%`;
  }

  function formatDuration(days: number): string {
    if (days % 365 === 0) {
      const years = days / 365;
      return `${years} ${years === 1 ? "year" : "years"}`;
    }
    return `${days} ${days === 1 ? "day" : "days"}`;
  }

  return (
    <main className="landing">
      <header className="landing-nav">
        <Link className="brand landing-brand" href="/" aria-label="WorkBit home"><i>W</i><span>WorkBit</span></Link>
        <nav aria-label="Main navigation">
          <Link href="/">Home</Link><Link href="/offers">Offers</Link><a href="#how-it-works">How it works</a><a href="#faq">FAQ</a>
        </nav>
        <div className="nav-actions"><Button variant="ghost" asChild><Link href="/login">Log in</Link></Button><Button className="primary" asChild><Link href="/register">Get started <ArrowUpRight size={15} /></Link></Button></div>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">A CLEARER WAY TO EARN</span>
          <h1>Make your next task <span>count.</span></h1>
          <p>Discover offers, complete the requirements, and follow every verified reward in one transparent account.</p>
          <div className="hero-actions"><Button className="primary" asChild><Link href="/register">Start earning</Link></Button><Button className="secondary" variant="outline" asChild><Link href="/offers">Explore offers <span aria-hidden="true">→</span></Link></Button></div>
          <p className="hero-footnote">No earnings promises. Rewards depend on offer terms and provider confirmation.</p>
        </div>
        <div className="hero-visual" aria-label="Illustration of an offer and its verification status">
          <div className="visual-orbit orbit-one" /><div className="visual-orbit orbit-two" />
          <Card className="visual-card offer-preview" asChild><article><span className="preview-icon">✦</span><div><small>OFFER ACTIVITY</small><strong>Task submitted</strong></div><span className="preview-check">✓</span></article></Card>
          <Card className="visual-card balance-preview" asChild><article><small>REWARD STATUS</small><strong>Verification in progress</strong><div className="progress-track"><i /></div><span>Provider confirmation required</span></article></Card>
          <div className="visual-stamp">TRACKED<br />BY LEDGER</div>
        </div>
      </section>

      <section className="public-stats" aria-label="Live WorkBit platform statistics">
        <div className="public-stats-heading">
          <span className="eyebrow">WORKBIT IN NUMBERS</span>
          <span><i aria-hidden="true" /> Live platform data</span>
        </div>
        <div className="public-stats-grid">
          {statsError ? (
            <p className="public-stats-message" role="status">{statsError}</p>
          ) : publicStats ? (
            publicStatItems.map(({ key, label, icon: Icon, tone }) => (
              <article className="public-stat-card" key={key}>
                <span className={`public-stat-icon ${tone}`} aria-hidden="true">
                  <Icon size={23} strokeWidth={2} />
                </span>
                <strong className={key === "total_payouts_bdt" ? "payout-stat" : ""}>
                  {formatStat(key)}
                </strong>
                <span className="public-stat-label">{label}</span>
                {key === "offer_approval_rate" && publicStats.offer_approval_rate === null && (
                  <small className="public-stat-note">No reviewed offers yet</small>
                )}
              </article>
            ))
          ) : (
            publicStatItems.map(({ key, label, tone }) => (
              <article className="public-stat-card is-loading" key={key} aria-hidden="true">
                <span className={`public-stat-icon ${tone}`} />
                <span className="public-stat-value-skeleton" />
                <span className="public-stat-label">{label}</span>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="section-wrap package-section" id="earning-packages">
        <div className="section-heading section-heading-row">
          <div>
            <span className="eyebrow">CHOOSE YOUR ACCESS</span>
            <h2>Our Earning Packages</h2>
            <p>Pick the access period that works for you. Offers and earnings are not guaranteed.</p>
          </div>
          <Link className="text-link" href="/packages">Package details <span aria-hidden="true">→</span></Link>
        </div>
        {packagesLoading ? (
          <div className="package-grid" aria-label="Loading earning packages">
            {[1, 2, 3, 4, 5, 6].map((item) => (
              <Card className="package-preview-card package-preview-loading" key={item}>
                <Skeleton className="h-5 w-1/3" />
                <Skeleton className="h-10 w-1/2" />
                <Skeleton className="h-4 w-2/3" />
              </Card>
            ))}
          </div>
        ) : packagesError ? (
          <Alert className="state error-state" variant="destructive" role="alert">
            <AlertDescription>{packagesError}</AlertDescription>
          </Alert>
        ) : packages.length ? (
          <div className="package-grid">
            {packages.map((item, index) => (
              <Card
                className={`package-preview-card${index === 1 ? " package-preview-featured" : ""}`}
                key={item.code}
              >
                <div className="package-preview-topline">
                  <span className="package-preview-icon" aria-hidden="true">
                    {index === 1 ? <Sparkles size={19} /> : <PackageCheck size={19} />}
                  </span>
                  <span className={`package-term-tag${index === 1 ? " featured" : ""}`}>
                    {formatDuration(item.duration_days)}
                  </span>
                </div>
                <p className="package-preview-kicker">{item.duration_days >= 730 ? "LONG-TERM ACCESS" : "GET STARTED"}</p>
                <h3>{item.name}</h3>
                <div className="package-preview-price">
                  <strong>
                    {formatUsd(item.amount, { minimumFractionDigits: 0 })}
                  </strong>
                  <span>/{formatDuration(item.duration_days)}</span>
                </div>
                <p className="package-preview-description">
                  {item.description || "Time-limited access to eligible WorkBit earning features."}
                </p>
                <ul className="package-preview-points">
                  <li><Check size={15} /> Access active after approval</li>
                  <li><Clock3 size={15} /> {formatDuration(item.duration_days)} of package access</li>
                </ul>
                <Button className={index === 1 ? "primary package-preview-cta featured" : "secondary package-preview-cta"} variant={index === 1 ? "default" : "outline"} asChild>
                  <Link href="/packages">View package <span aria-hidden="true">→</span></Link>
                </Button>
              </Card>
            ))}
          </div>
        ) : (
          <div className="empty featured-empty">
            <strong>No earning packages are available right now.</strong>
            <span>Please check back later.</span>
          </div>
        )}
      </section>

      <section className="section-wrap" id="how-it-works">
        <div className="section-heading"><span className="eyebrow">SIMPLE BY DESIGN</span><h2>From offer to verified reward</h2><p>Know what happens at each step, before you get started.</p></div>
        <div className="steps-grid">{steps.map(([number, title, copy]) => <Card className="step-card" key={number}><span>{number}</span><h3>{title}</h3><p>{copy}</p></Card>)}</div>
      </section>

      <section className="category-section">
        <div className="section-wrap category-inner">
          <div><span className="eyebrow">FIND YOUR NEXT TASK</span><h2>Different ways to get started</h2><p>Offer availability can vary by country, device, and provider.</p></div>
          <div className="category-chips">{["Apps", "Games", "Surveys", "Signups", "Websites", "More offers"].map((item) => <Link href="/offers" key={item}>{item}<span aria-hidden="true">↗</span></Link>)}</div>
        </div>
      </section>

      <section className="section-wrap featured-section">
        <div className="section-heading section-heading-row"><div><span className="eyebrow">LIVE FROM THE CATALOG</span><h2>Offers to explore</h2><p>Offer data comes from the configured catalog; availability may change.</p></div><Link className="text-link" href="/offers">Browse all offers →</Link></div>
        {loading ? <div className="featured-grid" aria-label="Loading offers">{[1, 2, 3].map((item) => <Card className="featured-card skeleton" key={item}><Skeleton className="h-5 w-2/3" /><Skeleton className="h-4 w-1/2" /></Card>)}</div>
          : offerError ? <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{offerError}</AlertDescription></Alert>
          : offers.length ? <div className="featured-grid">{offers.map((offer) => <Card className="featured-card" key={offer.id} asChild><Link href={`/offers/${encodeURIComponent(offer.id)}`}><Badge className="offer-category" variant="outline">{offer.category}</Badge><h3>{offer.title}</h3><p>{offer.short_description}</p><div className="featured-foot"><span>{offer.estimated_time_minutes ? `${offer.estimated_time_minutes} min` : "See requirements"}</span><strong>{formatUsd(offer.user_reward)}</strong></div>{offer.is_demo && <small className="demo-label">Development demo offer</small>}</Link></Card>)}</div>
          : <div className="empty featured-empty"><strong>No offers are available right now.</strong><span>Check back later or browse the catalog for updates.</span></div>}
      </section>

      <section className="benefit-band"><div className="section-wrap benefits"><div><span className="eyebrow">BUILT AROUND CLARITY</span><h2>Know what is pending.<br />Know what is available.</h2></div><div className="benefit-list"><p><b>01</b><span><strong>Transparent status</strong>Understand when an offer is awaiting provider confirmation.</span></p><p><b>02</b><span><strong>Wallet records</strong>Balances reflect backend ledger transactions, not browser estimates.</span></p><p><b>03</b><span><strong>Careful verification</strong>Conversions are reviewed before a reward is decided.</span></p></div></div></section>

      <section className="section-wrap faq-section" id="faq">
        <div className="faq-visual" role="img" aria-label="Illustration of earning categories: apps, games, surveys, and tasks">
          <div className="faq-visual-glow" />
          <div className="faq-visual-window">
            <div className="faq-visual-window-head"><span><i /><i /><i /></span><small>EXPLORE CATEGORIES</small><ShieldCheck size={16} /></div>
            <div className="faq-visual-title"><span className="eyebrow">YOUR NEXT OPPORTUNITY</span><strong>Find a task<br />that fits you.</strong></div>
            <div className="faq-category-tiles">
              <div><span className="faq-category-icon mint"><Smartphone size={19} /></span><b>Apps</b><small>Discover</small></div>
              <div><span className="faq-category-icon blue"><Gamepad2 size={19} /></span><b>Games</b><small>Play & explore</small></div>
              <div><span className="faq-category-icon violet"><ClipboardList size={19} /></span><b>Surveys</b><small>Share feedback</small></div>
              <div><span className="faq-category-icon gold"><Check size={19} /></span><b>Tasks</b><small>Complete steps</small></div>
            </div>
            <div className="faq-visual-foot"><span><i /> Clear requirements</span><span>Explore offers <ArrowUpRight size={13} /></span></div>
          </div>
          <div className="faq-visual-badge"><span><ShieldCheck size={18} /></span><div><b>Built on clarity</b><small>Track every step</small></div></div>
        </div>
        <div className="faq-content">
          <div className="section-heading"><span className="eyebrow">GOOD TO KNOW</span><h2>Frequently asked questions</h2><p>Clear answers before you get started.</p></div>
          <Accordion className="faq-grid" type="single" collapsible>
            <AccordionItem className="faq-item" value="reward"><AccordionTrigger className="faq-question">When does a reward appear?</AccordionTrigger><AccordionContent className="faq-answer">After a provider reports a conversion and it passes server-side validation, WorkBit records the reward decision. Some rewards may remain pending.</AccordionContent></AccordionItem>
            <AccordionItem className="faq-item" value="eligibility"><AccordionTrigger className="faq-question">Can every offer be completed?</AccordionTrigger><AccordionContent className="faq-answer">Availability and requirements vary by provider, country, and device. Review the offer details before starting.</AccordionContent></AccordionItem>
            <AccordionItem className="faq-item" value="payment"><AccordionTrigger className="faq-question">Does completing a task guarantee payment?</AccordionTrigger><AccordionContent className="faq-answer">No. The provider must confirm the conversion and the reward must satisfy the applicable policy.</AccordionContent></AccordionItem>
            <AccordionItem className="faq-item" value="activity"><AccordionTrigger className="faq-question">Where can I see reward activity?</AccordionTrigger><AccordionContent className="faq-answer">Sign in to view wallet balances, reward decisions, and ledger transactions associated with your account.</AccordionContent></AccordionItem>
          </Accordion>
        </div>
      </section>

      <section className="final-cta"><span className="eyebrow">YOUR NEXT STEP</span><h2>Explore with clear expectations.</h2><p>Create an account to view your wallet and keep track of verified offer activity.</p><Button className="primary" asChild><Link href="/register">Create your WorkBit account</Link></Button></section>

      <footer className="landing-footer">
        <div className="landing-footer-main">
          <div className="landing-footer-brand">
            <Link className="brand landing-brand" href="/"><i>W</i><span>WorkBit</span></Link>
            <p>Work. Complete. Earn.<br />A clearer way to track provider-verified rewards.</p>
          </div>
          <div className="landing-footer-column"><strong>Explore</strong><Link href="/offers">Browse offers</Link><Link href="/packages">Earning packages</Link><a href="#how-it-works">How it works</a></div>
          <div className="landing-footer-column"><strong>Your account</strong><Link href="/register">Create account</Link><Link href="/login">Log in</Link><a href="#faq">FAQs</a></div>
          <div className="landing-footer-column"><strong>Policies</strong><Link href="/terms">Terms of service</Link><Link href="/privacy">Privacy policy</Link><Link href="/reward-policy">Reward policy</Link><Link href="/withdrawal-policy">Withdrawal policy</Link></div>
        </div>
        <div className="landing-footer-bottom"><small>Rewards depend on offer eligibility, provider validation, and applicable policy. No earnings are guaranteed.</small><span>© {new Date().getFullYear()} WorkBit</span></div>
      </footer>
    </main>
  );
}
