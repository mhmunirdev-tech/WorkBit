"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Clock3, Gamepad2, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import { Shell } from "./shell";
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
  is_demo: boolean;
};

const categories = ["All", "GAME", "SURVEY", "APP", "SIGNUP", "OTHER"];

function reward(value: string, currency: string) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(Number(value));
}

export function OffersPage() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [category, setCategory] = useState("All");
  const [device, setDevice] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
    let active = true;
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ country: "US", limit: "100" });
    if (category !== "All") params.set("category", category);
    if (device) params.set("device", device);
    api<Offer[]>(`/offers?${params.toString()}`)
      .then((data) => { if (active) setOffers(data); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Offers could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [category, device]);

  const visibleOffers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return query ? offers.filter((offer) => `${offer.title} ${offer.short_description} ${offer.category}`.toLocaleLowerCase().includes(query)) : offers;
  }, [offers, search]);

  return (
    <Shell>
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
            <div className="offer-art"><Badge variant="secondary">{offer.device_type}</Badge>{offer.category === "GAME" ? <Gamepad2 /> : offer.category === "SURVEY" ? <Clock3 /> : <Sparkles />}</div>
            <CardContent className="offer-body"><Badge className="offer-type" variant="outline">{offer.category}</Badge><CardTitle>{offer.title}</CardTitle><p>{offer.short_description}</p><div className="meta"><span>{offer.estimated_time_minutes ? `${offer.estimated_time_minutes} min` : "Time varies"}</span><span>{offer.difficulty}</span><span>{offer.country}</span></div>
              <div className="offer-foot"><strong>{reward(offer.user_reward, offer.currency)}</strong><Button className="offer-link-button" variant="outline" asChild><Link href={`/offers/${encodeURIComponent(offer.id)}`}>View details <ArrowRight size={14} /></Link></Button></div>
              {offer.is_demo && <small className="demo-label">Development demo — no provider redirect</small>}
            </CardContent>
          </Card>)}
        </section> : !error && <div className="empty"><strong>No matching offers</strong><span>Try another search or filter. Catalog availability can change.</span></div>}
      <p className="disclaimer">Offer completion and rewards are subject to provider requirements, eligibility, and server-side validation. A displayed reward is not a payment guarantee.</p>
    </Shell>
  );
}

export function OfferDetailPage({ id }: { id: string }) {
  const [offer, setOffer] = useState<Offer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    api<Offer>(`/offers/${encodeURIComponent(id)}?country=US`)
      .then((data) => { if (active) setOffer(data); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Offer details could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  async function trackClick() {
    setBusy(true);
    setMessage("");
    try {
      const result = await api<{ message: string }>(`/offers/${encodeURIComponent(id)}/click`, { method: "POST" });
      setMessage(result.message);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Sign in to record an offer click.");
    } finally {
      setBusy(false);
    }
  }

  return <Shell>
    <Button variant="link" asChild><Link href="/offers" className="text-link"><ArrowLeft size={15} /> Back to offers</Link></Button>
    {loading ? <Card className="panel"><Skeleton className="h-5 w-1/2" /><Skeleton className="h-4 w-1/3" /></Card>
      : error || !offer ? <Alert className="state error-state" variant="destructive"><AlertDescription>{error || "Offer not found."}</AlertDescription></Alert>
      : <Card className="offer-detail panel"><CardContent><Badge className="offer-type" variant="outline">{offer.category} · {offer.country} · {offer.device_type}</Badge><h1>{offer.title}</h1><p>{offer.short_description}</p><div className="detail-reward"><span>Displayed reward</span><strong>{reward(offer.user_reward, offer.currency)}</strong></div><dl><div><dt>Estimated time</dt><dd>{offer.estimated_time_minutes ? `${offer.estimated_time_minutes} minutes` : "Varies by task"}</dd></div><div><dt>Difficulty</dt><dd>{offer.difficulty}</dd></div><div><dt>Availability</dt><dd>{offer.country} · {offer.device_type}</dd></div></dl><p className="offer-terms">Read and follow the provider’s full requirements. Rewards require provider confirmation and WorkBit validation.</p><Button className="primary" onClick={trackClick} disabled={busy}>{busy ? "Recording…" : "Record offer click"}</Button>{offer.is_demo && <p className="demo-label">Development demo offer. External provider redirects are disabled.</p>}{message && <Alert className="form-message" role="status"><AlertDescription>{message}</AlertDescription></Alert>}</CardContent></Card>}
  </Shell>;
}
