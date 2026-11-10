"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { MessageCircle, Plus, RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import { Shell } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Textarea } from "./ui/textarea";

type TicketMessage = {
  id: string;
  sender_role: "USER" | "ADMIN";
  body: string;
  created_at: string;
};

type Ticket = {
  id: string;
  subject: string;
  category: string;
  status: "OPEN" | "IN_PROGRESS" | "RESOLVED";
  created_at: string;
  updated_at: string;
  messages: TicketMessage[];
};

const categoryLabels: Record<string, string> = {
  OFFER_REWARD: "Offer or missing reward",
  WITHDRAWAL: "Withdrawal",
  ACCOUNT: "Account",
  OTHER: "Other",
};

function statusLabel(status: Ticket["status"]) {
  if (status === "IN_PROGRESS") return "In progress";
  return status.charAt(0) + status.slice(1).toLowerCase();
}

export function SupportPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState("OFFER_REWARD");
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const result = await api<Ticket[]>("/support/tickets");
      setTickets(result);
      setSelectedId((current) => result.some((ticket) => ticket.id === current) ? current : result[0]?.id ?? "");
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Support requests could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  async function createTicket(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const ticket = await api<Ticket>("/support/tickets", {
        method: "POST",
        body: JSON.stringify({ subject, category, message }),
      });
      setTickets((current) => [ticket, ...current]);
      setSelectedId(ticket.id);
      setSubject("");
      setMessage("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Your support request could not be submitted.");
    } finally {
      setSaving(false);
    }
  }

  async function sendReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTicket) return;
    setSaving(true);
    setError("");
    try {
      const updated = await api<Ticket>(`/support/tickets/${encodeURIComponent(selectedTicket.id)}/messages`, {
        method: "POST",
        body: JSON.stringify({ message: reply }),
      });
      setTickets((current) => current.map((ticket) => ticket.id === updated.id ? updated : ticket));
      setReply("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Your reply could not be sent.");
    } finally {
      setSaving(false);
    }
  }

  const selectedTicket = tickets.find((ticket) => ticket.id === selectedId);

  return (
    <Shell>
      <header className="top">
        <div><p className="eyebrow">HELP CENTER</p><h1>Support</h1><p className="muted">Report an offer or reward issue, and track replies from the WorkBit team.</p></div>
        <Button type="button" variant="outline" onClick={() => void refresh()}><RefreshCw size={15} /> Refresh</Button>
      </header>
      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      <div className="support-page-grid">
        <Card className="panel support-create-panel">
          <div className="panel-heading"><div><p className="eyebrow">NEW REQUEST</p><h2>How can we help?</h2></div><MessageCircle size={20} /></div>
          <form onSubmit={(event) => void createTicket(event)}>
            <Label>Topic<Select value={category} onValueChange={setCategory}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{Object.entries(categoryLabels).map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}</SelectContent></Select></Label>
            <Label>Subject<Input value={subject} onChange={(event) => setSubject(event.target.value)} minLength={5} maxLength={120} required /></Label>
            <Label>Details<Textarea value={message} onChange={(event) => setMessage(event.target.value)} minLength={10} maxLength={4000} rows={6} required placeholder="Include the offer name and approximate completion date if reporting a missing reward. Do not include passwords or payment codes." /></Label>
            <Button className="primary" type="submit" disabled={saving}><Plus size={16} /> {saving ? "Submitting…" : "Submit support request"}</Button>
          </form>
        </Card>
        <Card className="panel support-ticket-list">
          <div className="panel-heading"><div><p className="eyebrow">YOUR REQUESTS</p><h2>Ticket history</h2></div><span>{tickets.length}</span></div>
          {loading ? <p role="status">Loading your requests…</p> : tickets.length ? (
            <div className="support-ticket-items">{tickets.map((ticket) => (
              <button type="button" key={ticket.id} className={`support-ticket-button${ticket.id === selectedId ? " is-selected" : ""}`} onClick={() => setSelectedId(ticket.id)}>
                <span><strong>{ticket.subject}</strong><small>{categoryLabels[ticket.category] ?? ticket.category} · {new Date(ticket.updated_at).toLocaleDateString()}</small></span>
                <Badge variant="outline">{statusLabel(ticket.status)}</Badge>
              </button>
            ))}</div>
          ) : <p className="muted">No support requests yet.</p>}
        </Card>
        {selectedTicket && (
          <Card className="panel support-conversation">
            <div className="panel-heading"><div><p className="eyebrow">{categoryLabels[selectedTicket.category] ?? selectedTicket.category}</p><h2>{selectedTicket.subject}</h2></div><Badge variant="outline">{statusLabel(selectedTicket.status)}</Badge></div>
            <div className="support-messages">
              {selectedTicket.messages.map((item) => <article className={`support-message support-message-${item.sender_role.toLowerCase()}`} key={item.id}>
                <strong>{item.sender_role === "ADMIN" ? "WorkBit Support" : "You"}</strong>
                <p>{item.body}</p>
                <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time>
              </article>)}
            </div>
            {selectedTicket.status !== "RESOLVED" ? (
              <form className="support-reply-form" onSubmit={(event) => void sendReply(event)}>
                <Label htmlFor="support-reply">Add a message</Label>
                <Textarea id="support-reply" value={reply} onChange={(event) => setReply(event.target.value)} maxLength={4000} rows={3} required />
                <Button type="submit" variant="outline" disabled={saving}>{saving ? "Sending…" : "Send reply"}</Button>
              </form>
            ) : <p className="muted">This ticket is resolved. Create a new request if you still need help.</p>}
          </Card>
        )}
      </div>
    </Shell>
  );
}
