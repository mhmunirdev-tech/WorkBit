"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, ShieldAlert } from "lucide-react";
import { api } from "../lib/api";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";

type FraudEvent = {
  id: string;
  user_id: string | null;
  user_email: string | null;
  event_type: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  status: string;
  reason: string;
  evidence: Record<string, unknown>;
  ip_fingerprint: string | null;
  review_note: string | null;
  reviewed_at: string | null;
  created_at: string;
};

type FraudOverview = {
  open_medium: number;
  open_high: number;
  under_review: number;
  confirmed: number;
  events_today: number;
};

export function AdminFraud() {
  const [overview, setOverview] = useState<FraudOverview | null>(null);
  const [events, setEvents] = useState<FraudEvent[]>([]);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyEvent, setBusyEvent] = useState("");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextOverview, nextEvents] = await Promise.all([
        api<FraudOverview>("/admin/fraud/overview"),
        api<FraudEvent[]>("/admin/fraud/events?page_size=100"),
      ]);
      setOverview(nextOverview);
      setEvents(nextEvents);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Fraud records could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function reviewEvent(event: FraudEvent, status: "UNDER_REVIEW" | "CLEARED") {
    setBusyEvent(event.id);
    setError("");
    try {
      await api(`/admin/fraud/events/${event.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status,
          note: reason.trim() || (status === "CLEARED" ? "Reviewed and cleared." : "Review started."),
        }),
      });
      setReason("");
      await refresh();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Fraud event could not be updated.");
    } finally {
      setBusyEvent("");
    }
  }

  async function updateAccount(event: FraudEvent, status: "PENDING_REVIEW" | "SUSPENDED" | "BANNED" | "ACTIVE") {
    if (!event.user_id || reason.trim().length < 3) {
      setError("Enter a reason of at least 3 characters before changing an account.");
      return;
    }
    if (status === "BANNED" && !window.confirm("Permanently ban this user account?")) return;
    setBusyEvent(event.id);
    setError("");
    try {
      await api(`/admin/fraud/users/${event.user_id}/status`, {
        method: "POST",
        body: JSON.stringify({ status, reason: reason.trim() }),
      });
      await refresh();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Account status could not be updated.");
    } finally {
      setBusyEvent("");
    }
  }

  return (
    <main className="admin-users-page">
      <header className="admin-withdrawals-header admin-users-header">
        <div>
          <p className="eyebrow">RISK &amp; ACCOUNT SAFETY</p>
          <h1>Fraud management</h1>
          <p>Review evidence-backed signals. Shared IP addresses are indicators for review, never automatic grounds for a ban.</p>
        </div>
        <Button className="secondary-button" variant="outline" type="button" onClick={() => void refresh()} disabled={loading}>
          <RefreshCw size={15} /> Refresh
        </Button>
      </header>

      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}

      <section className="admin-user-summary" aria-label="Fraud overview">
        <Card className="admin-user-summary-card"><ShieldAlert size={17} /><span><small>Open medium risk</small><strong>{overview?.open_medium ?? "—"}</strong></span></Card>
        <Card className="admin-user-summary-card"><span><small>Open high risk</small><strong>{overview?.open_high ?? "—"}</strong></span></Card>
        <Card className="admin-user-summary-card"><span><small>Under review</small><strong>{overview?.under_review ?? "—"}</strong></span></Card>
        <Card className="admin-user-summary-card"><span><small>Confirmed</small><strong>{overview?.confirmed ?? "—"}</strong></span></Card>
        <Card className="admin-user-summary-card"><span><small>Events today</small><strong>{overview?.events_today ?? "—"}</strong></span></Card>
      </section>

      <Card className="admin-user-registry-card">
        <label className="admin-fraud-reason">
          Review or account-action reason
          <Input value={reason} onChange={(event) => setReason(event.target.value)} maxLength={500} placeholder="Record the evidence-based reason for your action" />
        </label>
        {loading ? <p className="state" role="status">Loading fraud events…</p> : events.length ? (
          <div className="admin-user-table-wrap">
            <table className="admin-user-table">
              <thead><tr><th>Signal</th><th>Risk / status</th><th>Evidence</th><th>IP fingerprint</th><th>Actions</th></tr></thead>
              <tbody>{events.map((event) => (
                <tr key={event.id}>
                  <td><strong>{event.event_type.replaceAll("_", " ")}</strong><span>{event.user_email || "No linked account"}</span><small>{event.reason}</small><small>{new Date(event.created_at).toLocaleString()}</small></td>
                  <td><Badge variant="outline">{event.risk_level}</Badge><small>{event.status.replaceAll("_", " ")}</small></td>
                  <td><code>{JSON.stringify(event.evidence)}</code>{event.review_note && <small>Review: {event.review_note}</small>}</td>
                  <td>{event.ip_fingerprint || "Not recorded"}</td>
                  <td className="admin-fraud-actions">
                    {event.status === "OPEN" && <>
                      <Button type="button" variant="outline" size="sm" disabled={busyEvent === event.id} onClick={() => void reviewEvent(event, "UNDER_REVIEW")}>Review</Button>
                      <Button type="button" variant="outline" size="sm" disabled={busyEvent === event.id} onClick={() => void reviewEvent(event, "CLEARED")}>Clear</Button>
                    </>}
                    {event.user_id && <>
                      <Button type="button" variant="outline" size="sm" disabled={busyEvent === event.id} onClick={() => void updateAccount(event, "PENDING_REVIEW")}>Restrict</Button>
                      <Button type="button" variant="outline" size="sm" disabled={busyEvent === event.id} onClick={() => void updateAccount(event, "SUSPENDED")}>Suspend</Button>
                      <Button type="button" variant="outline" size="sm" disabled={busyEvent === event.id} onClick={() => void updateAccount(event, "BANNED")}>Ban</Button>
                      <Button type="button" variant="outline" size="sm" disabled={busyEvent === event.id} onClick={() => void updateAccount(event, "ACTIVE")}>Restore</Button>
                    </>}
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <p className="state">No fraud events have been recorded.</p>}
      </Card>
    </main>
  );
}
