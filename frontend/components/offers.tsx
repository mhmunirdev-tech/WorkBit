"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Clock3, Gamepad2, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import { useLiveRefresh } from "../lib/use-live-refresh";
import { showToast } from "../lib/toast";
import { formatUsd } from "../lib/utils";
import { Shell, useShellUser, WALLET_UPDATED_EVENT } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardTitle } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Skeleton } from "./ui/skeleton";

type Offer = {
  id: string;
  title: string;
  short_description: string;
  category: string;
  country: string;
  device_type: string;
  user_reward: string;
  currency: string;
  estimated_time_minutes: number;
  difficulty: string;
  featured: boolean;
  source_name: string;
  is_demo: boolean;
};

const categories = ["All", "GAME", "SURVEY", "APP", "SIGNUP", "OTHER"];

function reward(value: string, currency: string) {
  return formatUsd(value);
}

function OffersCatalog() {
  const account = useShellUser();
  const [offers, setOffers] = useState<Offer[]>([]);
  const [category, setCategory] = useState("All");
  const [device, setDevice] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const refreshOffers = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    setError("");
    const params = new URLSearchParams({ limit: "100" });
    if (account?.country) params.set("country", account.country);
    if (category !== "All") params.set("category", category);
    if (device) params.set("device", device);
    try {
      setOffers(await api<Offer[]>(`/offers?${params.toString()}`));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Offers could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [account?.country, category, device]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const query = params.get("search");
    const initialCategory = params.get("category");
    if (query) setSearch(query);
    if (initialCategory && categories.includes(initialCategory.toUpperCase())) {
      setCategory(initialCategory.toUpperCase());
    }
  }, []);

  useEffect(() => {
    void refreshOffers(true);
  }, [refreshOffers]);
  useLiveRefresh(refreshOffers);

  const visibleOffers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return query ? offers.filter((offer) => `${offer.title} ${offer.short_description} ${offer.category}`.toLocaleLowerCase().includes(query)) : offers;
  }, [offers, search]);

  return (
    <>
      <header className="top"><div><p className="eyebrow">OFFER CATALOG</p><h1>Find your next task</h1><p className="muted">Availability and rewards depend on offer terms and provider verification.</p></div></header>
      <section className="offer-controls" aria-label="Offer filters">
        <Label className="search-control">Search offers<Input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by title or category" /></Label>
        <Label>Category<Select value={category} onValueChange={setCategory}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{categories.map((item) => <SelectItem key={item} value={item}>{item === "All" ? "All categories" : item[0] + item.slice(1).toLowerCase()}</SelectItem>)}</SelectContent></Select></Label>
        <Label>Device<Select value={device || "ANY"} onValueChange={(value) => setDevice(value === "ANY" ? "" : value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ANY">Any device</SelectItem><SelectItem value="WEB">Web</SelectItem><SelectItem value="IOS">iOS</SelectItem><SelectItem value="ANDROID">Android</SelectItem></SelectContent></Select></Label>
      </section>
      {error && <Alert className="state error-state" variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {loading ? <section className="offer-grid" aria-label="Loading offer catalog">{[1, 2, 3].map((item) => <Card className="offer skeleton" key={item}><CardContent className="offer-body"><Skeleton className="h-5 w-2/3" /><Skeleton className="h-4 w-1/2" /></CardContent></Card>)}</section>
        : !error && visibleOffers.length ? <section className="offer-grid" aria-label="Available offers">
          {visibleOffers.map((offer) => <Card className="offer" key={offer.id}>
            <div className={`offer-art offer-art-${offer.category.toLowerCase()}`}>
              <div className="offer-art-topline"><span className="offer-art-label">{offer.featured ? "FEATURED OFFER" : "DISCOVER & EARN"}</span><Badge variant="secondary">{offer.device_type}</Badge></div>
              <span className="offer-art-icon">{offer.category === "GAME" ? <Gamepad2 /> : offer.category === "SURVEY" ? <Clock3 /> : <Sparkles />}</span>
            </div>
            <CardContent className="offer-body">
              <div className="offer-badges"><Badge className="offer-provider" variant="secondary">{offer.source_name}</Badge><Badge className="offer-type" variant="outline">{offer.category}</Badge></div>
              <CardTitle>{offer.title}</CardTitle>
              <p>{offer.short_description}</p>
              <div className="meta"><span>{offer.estimated_time_minutes ? `${offer.estimated_time_minutes} min` : "Time varies"}</span><span>{offer.difficulty}</span><span>{offer.country}</span></div>
              <div className="offer-foot"><div className="offer-reward"><small>GROSS AD REWARD</small><strong>{reward(offer.user_reward, offer.currency)}</strong></div><Button className="offer-link-button" variant="outline" asChild><Link href={`/offers/${encodeURIComponent(offer.id)}`}>View details <ArrowRight size={14} /></Link></Button></div>
              {offer.is_demo && <small className="demo-label">Development demo — no provider redirect</small>}
            </CardContent>
          </Card>)}
        </section> : !error && <div className="empty"><strong>No matching offers</strong><span>Try another search or filter. Catalog availability can change.</span></div>}
      <p className="disclaimer">Offer completion and rewards are subject to provider requirements, eligibility, and server-side validation. A displayed reward is not a payment guarantee.</p>
    </>
  );
}

export function OffersPage() {
  return <Shell><OffersCatalog /></Shell>;
}

function OfferDetailContent({ id }: { id: string }) {
  const account = useShellUser();
  const [offer, setOffer] = useState<Offer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    const country = account?.country;
    const query = country ? `?country=${encodeURIComponent(country)}` : "";
    api<Offer>(`/offers/${encodeURIComponent(id)}${query}`)
      .then((data) => { if (active) setOffer(data); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Offer details could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [account?.country, id]);

  async function trackClick() {
    setBusy(true);
    setMessage("");
    try {
      const result = await api<{ message: string }>(
        `/offers/${encodeURIComponent(id)}/click`,
        { method: "POST" },
      );
      setMessage(result.message);
      showToast({ title: "Offer click recorded", description: result.message, variant: "success" });
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Sign in to record an offer click.";
      setMessage(message);
      showToast({ title: "Could not record offer click", description: message, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  }

  async function simulateCompletion() {
    setBusy(true);
    setMessage("");
    try {
      const result = await api<{ message: string }>(
        `/offers/${encodeURIComponent(id)}/simulate-completion`,
        { method: "POST" },
      );
      setMessage(result.message);
      window.dispatchEvent(new Event(WALLET_UPDATED_EVENT));
      showToast({ title: "Test ad completed", description: result.message, variant: "success" });
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Could not simulate ad completion.";
      setMessage(message);
      showToast({ title: "Could not complete test ad", description: message, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  }

  return <>
    <Button variant="link" asChild><Link href="/offers" className="text-link"><ArrowLeft size={15} /> Back to offers</Link></Button>
    {loading ? <Card className="panel"><Skeleton className="h-5 w-1/2" /><Skeleton className="h-4 w-1/3" /></Card>
      : error || !offer ? <Alert className="state error-state" variant="destructive"><AlertDescription>{error || "Offer not found."}</AlertDescription></Alert>
      : <Card className="offer-detail panel"><CardContent><Badge className="offer-provider" variant="secondary">{offer.source_name}</Badge><Badge className="offer-type" variant="outline">{offer.category} · {offer.country} · {offer.device_type}</Badge><h1>{offer.title}</h1><p>{offer.short_description}</p><div className="detail-reward"><span>Gross ad reward</span><strong>{reward(offer.user_reward, offer.currency)}</strong></div><dl><div><dt>Estimated time</dt><dd>{offer.estimated_time_minutes ? `${offer.estimated_time_minutes} minutes` : "Varies by task"}</dd></div><div><dt>Difficulty</dt><dd>{offer.difficulty}</dd></div><div><dt>Availability</dt><dd>{offer.country} · {offer.device_type}</dd></div></dl><p className="offer-terms">{offer.is_demo ? "This is a development test offer. 20% of the gross ad reward is retained as platform share; the remaining 80% is credited to your available balance." : "Read and follow the provider’s full requirements. Rewards require provider confirmation and WorkBit validation."}</p>{offer.is_demo ? <><p className="demo-label">Development demo only — no external ad is played.</p><Button className="primary" onClick={simulateCompletion} disabled={busy}>{busy ? "Adding test earning…" : "Complete demo ad and add test earning"}</Button></> : <Button className="primary" onClick={trackClick} disabled={busy}>{busy ? "Recording…" : "Record offer click"}</Button>}{message && <Alert className="form-message" role="status"><AlertDescription>{message}</AlertDescription></Alert>}{message.toLowerCase().includes("package") && <Button variant="outline" asChild><Link href="/packages">View earning packages</Link></Button>}</CardContent></Card>}
  </>;
}

export function OfferDetailPage({ id }: { id: string }) {
  return <Shell><OfferDetailContent id={id} /></Shell>;
}
