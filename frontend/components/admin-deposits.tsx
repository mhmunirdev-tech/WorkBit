"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { formatUsd } from "../lib/utils";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Textarea } from "./ui/textarea";

type Deposit = {
  id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  amount_bdt: string;
  amount: string;
  currency: string;
  exchange_rate: string;
  payment_method: string;
  payment_reference: string;
  status: string;
  admin_note: string | null;
  created_at: string;
};

function money(value: string, currency: string) {
  return formatUsd(value);
}

export function AdminDeposits() {
  const [deposits, setDeposits] = useState<Deposit[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setDeposits(await api<Deposit[]>("/admin/deposits"));
    } catch (reason) {
      setDeposits([]);
      setError(reason instanceof Error ? reason.message : "Deposit requests could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function review(deposit: Deposit, action: "approve" | "reject") {
    setBusyId(deposit.id);
    setError("");
    setMessage("");
    try {
      const updated = await api<Deposit>(`/admin/deposits/${deposit.id}/${action}`, {
        method: "POST",
        body: JSON.stringify({ note: notes[deposit.id]?.trim() || null }),
      });
      setDeposits((items) => items.map((item) => item.id === updated.id ? updated : item));
      const reviewMessage = `Deposit ${updated.status.toLowerCase()}.`;
      setMessage(reviewMessage);
      showToast({ title: "Deposit reviewed", description: reviewMessage, variant: "success" });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The deposit could not be reviewed.");
    } finally {
      setBusyId("");
    }
  }

  return (
    <main className="admin-withdrawals-page">
      <header className="admin-withdrawals-header">
        <div><p className="eyebrow">WORKBIT ADMIN</p><h1>Deposit requests</h1><p>Verify each bKash/Nagad transfer before crediting a user’s package balance.</p></div>
        <div className="admin-withdrawals-links">
          <Button className="secondary-button" variant="outline" type="button" onClick={() => void refresh()} disabled={loading || Boolean(busyId)}>Refresh</Button>
          <Button variant="link" asChild><Link href="/admin">Admin overview</Link></Button>
        </div>
      </header>
      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      {message && <Alert className="state" role="status"><AlertDescription>{message}</AlertDescription></Alert>}
      <Card className="panel admin-deposit-list">
        {loading ? <p className="state">Loading deposit requests…</p> : deposits.length === 0 ? (
          <p className="state">There are no deposit requests to review.</p>
        ) : deposits.map((deposit) => (
          <article className="admin-deposit-item" key={deposit.id}>
            <div className="admin-deposit-heading">
              <div><strong>{deposit.user_name}</strong><small>{deposit.user_email}</small></div>
              <Badge variant="outline">{deposit.status}</Badge>
            </div>
            <dl className="admin-deposit-details">
              <div><dt>Sent</dt><dd>{money(deposit.amount_bdt, "BDT")}</dd></div>
              <div><dt>Wallet credit</dt><dd>{money(deposit.amount, deposit.currency)}</dd></div>
              <div><dt>Method</dt><dd>{deposit.payment_method}</dd></div>
              <div><dt>Transaction ID</dt><dd>{deposit.payment_reference}</dd></div>
              <div><dt>USD/BDT rate</dt><dd>{deposit.exchange_rate}</dd></div>
              <div><dt>Submitted</dt><dd>{new Date(deposit.created_at).toLocaleString()}</dd></div>
            </dl>
            {deposit.status === "PENDING" ? (
              <>
                <Textarea
                  aria-label={`Admin note for ${deposit.user_email}`}
                  value={notes[deposit.id] ?? ""}
                  onChange={(event) => setNotes((current) => ({ ...current, [deposit.id]: event.target.value }))}
                  maxLength={500}
                  placeholder="Optional review note"
                />
                <div className="admin-deposit-actions">
                  <Button className="primary" type="button" disabled={Boolean(busyId)} onClick={() => void review(deposit, "approve")}>{busyId === deposit.id ? "Saving…" : "Approve and credit"}</Button>
                  <Button variant="outline" type="button" disabled={Boolean(busyId)} onClick={() => void review(deposit, "reject")}>Reject</Button>
                </div>
              </>
            ) : deposit.admin_note && <p className="muted">{deposit.admin_note}</p>}
          </article>
        ))}
      </Card>
    </main>
  );
}
