"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Textarea } from "./ui/textarea";

type Withdrawal = {
  id: string;
  amount: string | number;
  currency: string;
  method: string;
  destination_hint: string;
  status: string;
  created_at: string;
  updated_at: string;
};

type WithdrawalDetails = Withdrawal & {
  user_id: string;
  user_email: string;
  user_name: string;
  destination: string;
  admin_note: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
};

type Action = "approve" | "reject" | "complete";

function formatMoney(amount: string | number, currency: string) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(amount));
}

export function AdminWithdrawals() {
  const [records, setRecords] = useState<Withdrawal[]>([]);
  const [selected, setSelected] = useState<WithdrawalDetails | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      setRecords(await api<Withdrawal[]>("/admin/withdrawals"));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Withdrawal requests could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function viewDetails(withdrawal: Withdrawal) {
    setSelected(null);
    setError("");
    setMessage("");
    setBusy(true);
    try {
      setSelected(await api<WithdrawalDetails>(`/admin/withdrawals/${withdrawal.id}`));
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : "Payout details could not be loaded.");
    } finally {
      setBusy(false);
    }
  }

  async function review(action: Action) {
    if (!selected) return;
    if (action === "complete" && !window.confirm("Confirm this payout has been sent to the user's destination?")) return;

    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await api<Withdrawal>(`/admin/withdrawals/${selected.id}/${action}`, {
        method: "POST",
        body: JSON.stringify({ note: note.trim() || null }),
      });
      setRecords((existing) => existing.map((item) => item.id === updated.id ? updated : item));
      setSelected((existing) => existing ? { ...existing, status: updated.status, updated_at: updated.updated_at } : existing);
      setNote("");
      setMessage(`Withdrawal marked ${updated.status.toLowerCase()}.`);
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "The withdrawal could not be updated.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="admin-withdrawals-page">
      <header className="admin-withdrawals-header">
        <div>
          <p className="eyebrow">WORKBIT ADMIN</p>
          <h1>Manual withdrawals</h1>
          <p>Review user payout requests and record each manual decision.</p>
        </div>
        <div className="admin-withdrawals-links">
          <Button className="secondary-button" variant="outline" type="button" onClick={() => void refresh()} disabled={loading || busy}>Refresh</Button>
          <Button variant="link" asChild><Link href="/admin">Admin overview</Link></Button>
        </div>
      </header>

      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      {message && <Alert className="state" role="status"><AlertDescription>{message}</AlertDescription></Alert>}

      <div className="admin-withdrawals-layout">
        <Card className="panel admin-withdrawals-list" aria-label="Withdrawal requests">
          <div className="panel-heading"><div><p className="eyebrow">REQUEST QUEUE</p><h2>All requests</h2></div></div>
          {loading ? <p className="state">Loading withdrawal requests…</p> : records.length === 0 ? (
            <p className="state">There are no withdrawal requests to review.</p>
          ) : (
            <div className="admin-withdrawal-items">
              {records.map((record) => (
                <Button
                  variant="ghost"
                  className={`admin-withdrawal-item${selected?.id === record.id ? " is-selected" : ""}`}
                  type="button"
                  key={record.id}
                  onClick={() => void viewDetails(record)}
                  aria-pressed={selected?.id === record.id}
                >
                  <span><strong>{formatMoney(record.amount, record.currency)}</strong><small>{record.destination_hint}</small></span>
                  <Badge className={`withdrawal-status withdrawal-${record.status.toLowerCase()}`} variant="outline">{record.status.toLowerCase()}</Badge>
                  <time dateTime={record.created_at}>{new Date(record.created_at).toLocaleDateString()}</time>
                </Button>
              ))}
            </div>
          )}
        </Card>

        <Card className="panel admin-withdrawal-detail" aria-label="Selected withdrawal">
          {!selected ? (
            <div className="dashboard-empty">
              <strong>{busy ? "Loading secure payout details…" : "Select a request"}</strong>
              <span>Full payout details are fetched only when a reviewer opens a request. Each read is audited.</span>
            </div>
          ) : (
            <>
              <div className="panel-heading">
                <div><p className="eyebrow">REQUEST DETAILS</p><h2>{formatMoney(selected.amount, selected.currency)}</h2></div>
                <Badge className={`withdrawal-status withdrawal-${selected.status.toLowerCase()}`} variant="outline">{selected.status.toLowerCase()}</Badge>
              </div>
              <dl className="admin-withdrawal-fields">
                <div><dt>User</dt><dd>{selected.user_name} · {selected.user_email}</dd></div>
                <div><dt>Destination</dt><dd className="admin-destination">{selected.destination}</dd></div>
                <div><dt>Submitted</dt><dd><time dateTime={selected.created_at}>{new Date(selected.created_at).toLocaleString()}</time></dd></div>
                {selected.admin_note && <div><dt>Previous review note</dt><dd>{selected.admin_note}</dd></div>}
              </dl>

              {(selected.status === "PENDING" || selected.status === "PROCESSING") && (
                <div className="admin-withdrawal-review">
                  <label htmlFor="withdrawal-review-note">Review note (optional)</label>
                  <Textarea id="withdrawal-review-note" maxLength={500} value={note} onChange={(event) => setNote(event.target.value)} />
                  <div className="admin-withdrawal-actions">
                    {selected.status === "PENDING" && <Button className="primary" type="button" disabled={busy} onClick={() => void review("approve")}>Approve</Button>}
                    {selected.status === "PROCESSING" && <Button className="primary" type="button" disabled={busy} onClick={() => void review("complete")}>Mark as paid</Button>}
                    <Button className="secondary-button is-danger" variant="destructive" type="button" disabled={busy} onClick={() => void review("reject")}>Reject and release funds</Button>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </main>
  );
}
