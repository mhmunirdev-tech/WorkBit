"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
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

  return (
    <main className="landing">
      <header className="landing-nav">
        <Link className="brand landing-brand" href="/"><i>W</i> WorkBit</Link>
        <nav aria-label="Main navigation">
          <Link href="/">Home</Link><Link href="/offers">Offers</Link><a href="#how-it-works">How it works</a><a href="#faq">FAQ</a>
        </nav>
        <div className="nav-actions"><Button variant="ghost" asChild><Link href="/login">Log in</Link></Button><Button className="primary" asChild><Link href="/register">Get started</Link></Button></div>
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

      <section className="trust-strip" aria-label="WorkBit principles">
        <span>Provider-confirmed rewards</span><span>Clear pending status</span><span>Ledger-backed balances</span><span>No hidden payout claims</span>
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
          : offers.length ? <div className="featured-grid">{offers.map((offer) => <Card className="featured-card" key={offer.id} asChild><Link href={`/offers/${encodeURIComponent(offer.id)}`}><Badge className="offer-category" variant="outline">{offer.category}</Badge><h3>{offer.title}</h3><p>{offer.short_description}</p><div className="featured-foot"><span>{offer.estimated_time_minutes ? `${offer.estimated_time_minutes} min` : "See requirements"}</span><strong>{new Intl.NumberFormat(undefined, { style: "currency", currency: offer.currency }).format(Number(offer.user_reward))}</strong></div>{offer.is_demo && <small className="demo-label">Development demo offer</small>}</Link></Card>)}</div>
          : <div className="empty featured-empty"><strong>No offers are available right now.</strong><span>Check back later or browse the catalog for updates.</span></div>}
      </section>

      <section className="benefit-band"><div className="section-wrap benefits"><div><span className="eyebrow">BUILT AROUND CLARITY</span><h2>Know what is pending.<br />Know what is available.</h2></div><div className="benefit-list"><p><b>01</b><span><strong>Transparent status</strong>Understand when an offer is awaiting provider confirmation.</span></p><p><b>02</b><span><strong>Wallet records</strong>Balances reflect backend ledger transactions, not browser estimates.</span></p><p><b>03</b><span><strong>Careful verification</strong>Conversions are reviewed before a reward is decided.</span></p></div></div></section>

      <section className="section-wrap faq-section" id="faq"><div className="section-heading"><span className="eyebrow">GOOD TO KNOW</span><h2>Frequently asked questions</h2></div><Accordion className="faq-grid" type="single" collapsible>
        <AccordionItem className="faq-item" value="reward"><AccordionTrigger className="faq-question">When does a reward appear?</AccordionTrigger><AccordionContent className="faq-answer">After a provider reports a conversion and it passes server-side validation, WorkBit records the reward decision. Some rewards may remain pending.</AccordionContent></AccordionItem>
        <AccordionItem className="faq-item" value="eligibility"><AccordionTrigger className="faq-question">Can every offer be completed?</AccordionTrigger><AccordionContent className="faq-answer">Availability and requirements vary by provider, country, and device. Review the offer details before starting.</AccordionContent></AccordionItem>
        <AccordionItem className="faq-item" value="payment"><AccordionTrigger className="faq-question">Does completing a task guarantee payment?</AccordionTrigger><AccordionContent className="faq-answer">No. The provider must confirm the conversion and the reward must satisfy the applicable policy.</AccordionContent></AccordionItem>
        <AccordionItem className="faq-item" value="activity"><AccordionTrigger className="faq-question">Where can I see reward activity?</AccordionTrigger><AccordionContent className="faq-answer">Sign in to view wallet balances, reward decisions, and ledger transactions associated with your account.</AccordionContent></AccordionItem>
      </Accordion></section>

      <section className="final-cta"><span className="eyebrow">YOUR NEXT STEP</span><h2>Explore with clear expectations.</h2><p>Create an account to view your wallet and keep track of verified offer activity.</p><Button className="primary" asChild><Link href="/register">Create your WorkBit account</Link></Button></section>

      <footer className="landing-footer"><Link className="brand landing-brand" href="/"><i>W</i> WorkBit</Link><span>Work. Complete. Earn.</span><nav aria-label="Legal and information"><Link href="/about">About</Link><Link href="/terms">Terms</Link><Link href="/privacy">Privacy</Link><Link href="/reward-policy">Reward policy</Link><Link href="/withdrawal-policy">Withdrawal policy</Link><Link href="/contact">Contact</Link></nav><small>Rewards are subject to offer eligibility, provider validation, and applicable policy.</small></footer>
    </main>
  );
}
