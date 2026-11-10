"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Textarea } from "./ui/textarea";

type TicketMessage = { id: string; sender_role: "USER" | "ADMIN"; body: string; created_at: string };
type Ticket = {
  id: string; subject: string; category: string; status: "OPEN" | "IN_PROGRESS" | "RESOLVED";
  created_at: string; updated_at: string; user_id: string; user_name: string; user_email: string;
  messages: TicketMessage[];
};

export function AdminSupport() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [status, setStatus] = useState<Ticket["status"]>("IN_PROGRESS");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const query = filter === "ALL" ? "" : `?status=${filter}`;
      const result = await api<Ticket[]>(`/admin/support/tickets${query}`);
      setTickets(result);
      setSelectedId((current) => result.some((ticket) => ticket.id === current) ? current : result[0]?.id ?? "");
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Support tickets could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { void refresh(); }, [refresh]);

  const selected = tickets.find((ticket) => ticket.id === selectedId);

  async function reply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setSaving(true);
    setError("");
    try {
      const updated = await api<Ticket>(`/admin/support/tickets/${encodeURIComponent(selected.id)}/reply`, {
        method: "POST",
        body: JSON.stringify({ message, status }),
      });
      setTickets((current) => current.map((ticket) => ticket.id === updated.id ? updated : ticket));
      setMessage("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The support reply could not be sent.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="admin-console-page">
      <header className="top"><div><p className="eyebrow">CUSTOMER CARE</p><h1>Support tickets</h1><p className="muted">Review user requests and reply with a clear status.</p></div>
        <div className="admin-support-toolbar"><Select value={filter} onValueChange={setFilter}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ALL">All tickets</SelectItem><SelectItem value="OPEN">Open</SelectItem><SelectItem value="IN_PROGRESS">In progress</SelectItem><SelectItem value="RESOLVED">Resolved</SelectItem></SelectContent></Select><Button variant="outline" type="button" onClick={() => void refresh()}><RefreshCw size={15} /> Refresh</Button></div>
      </header>
      {error && <Alert className="state error-state" variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      <div className="admin-support-grid">
        <Card className="panel admin-support-list">
          {loading ? <p role="status">Loading support tickets…</p> : tickets.length ? tickets.map((ticket) => <button type="button" key={ticket.id} className={`support-ticket-button${ticket.id === selectedId ? " is-selected" : ""}`} onClick={() => { setSelectedId(ticket.id); setStatus(ticket.status); }}>
            <span><strong>{ticket.subject}</strong><small>{ticket.user_name} · {ticket.user_email}</small></span><Badge variant="outline">{ticket.status.toLowerCase().replace("_", " ")}</Badge>
          </button>) : <p className="muted">No tickets match this filter.</p>}
        </Card>
        {selected && <Card className="panel admin-support-detail">
          <p className="eyebrow">{selected.category.replaceAll("_", " ")}</p><h2>{selected.subject}</h2><p className="muted">{selected.user_name} · {selected.user_email}</p>
          <div className="support-messages">{selected.messages.map((item) => <article className={`support-message support-message-${item.sender_role.toLowerCase()}`} key={item.id}>
            <strong>{item.sender_role === "ADMIN" ? "WorkBit Support" : selected.user_name}</strong><p>{item.body}</p><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time>
          </article>)}</div>
          {selected.status !== "RESOLVED" && <form className="support-reply-form" onSubmit={(event) => void reply(event)}>
            <Label>Reply to user<Textarea value={message} onChange={(event) => setMessage(event.target.value)} rows={4} maxLength={4000} required /></Label>
            <Label>Update status<Select value={status} onValueChange={(value) => setStatus(value as Ticket["status"])}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="OPEN">Open</SelectItem><SelectItem value="IN_PROGRESS">In progress</SelectItem><SelectItem value="RESOLVED">Resolved</SelectItem></SelectContent></Select></Label>
            <Button className="primary" type="submit" disabled={saving}>{saving ? "Sending…" : "Send reply and update"}</Button>
          </form>}
        </Card>}
      </div>
    </div>
  );
}
