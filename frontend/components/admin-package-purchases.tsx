"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, Check, RefreshCw, X } from "lucide-react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { formatUsd } from "../lib/utils";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

type Purchase = {
  id: string;
  package_code: string;
  package_name: string;
  amount: string;
  currency: string;
  payment_amount_bdt: string | null;
  usd_bdt_rate: string | null;
  payment_method: string;
  payment_reference: string;
  status: string;
  admin_note: string | null;
  created_at: string;
  reviewed_at: string | null;
  user_id: string;
  user_name: string;
  user_email: string;
};

function money(amount: string, currency: string) {
  return formatUsd(amount);
}

export function AdminPackagePurchases() {
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setPurchases(await api<Purchase[]>("/admin/package-purchases"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Package payments could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function review(purchase: Purchase, action: "approve" | "reject") {
    const expected = purchase.payment_amount_bdt
      ? `BDT ${Number(purchase.payment_amount_bdt).toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : money(purchase.amount, purchase.currency);
    if (action === "approve" && !window.confirm(`Confirm receipt of ${expected} for ${purchase.package_name}?`)) return;
    setBusyId(purchase.id);
    setError("");
    setMessage("");
    try {
      const updated = await api<Purchase>(`/admin/package-purchases/${purchase.id}/${action}`, {
        method: "POST",
        body: JSON.stringify({ note: null }),
      });
      setPurchases((existing) => existing.map((item) => item.id === updated.id ? updated : item));
      const reviewMessage = `${updated.package_name} payment marked ${updated.status.toLowerCase()}.`;
      setMessage(reviewMessage);
      showToast({ title: "Package payment reviewed", description: reviewMessage, variant: "success" });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Package payment could not be reviewed.");
    } finally {
      setBusyId("");
    }
  }

  return (
    <main className="admin-package-page">
      <header className="admin-withdrawals-header">
        <div><p className="eyebrow">PAYMENT OPERATIONS</p><h1>Package payments</h1><p>Verify bKash and Nagad transaction references before unlocking ad earning.</p></div>
        <div className="admin-withdrawals-links">
          <Button className="secondary-button" variant="outline" type="button" onClick={() => void refresh()} disabled={loading}><RefreshCw size={15} /> Refresh</Button>
          <Button variant="link" asChild><Link href="/admin">Admin overview <ArrowUpRight size={14} /></Link></Button>
        </div>
      </header>
      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      {message && <Alert className="state" role="status"><AlertDescription>{message}</AlertDescription></Alert>}
      <Card className="panel admin-package-list">
        <div className="panel-heading"><div><p className="eyebrow">PAYMENT REVIEW</p><h2>Submitted transactions</h2></div></div>
        {loading ? <p className="state">Loading package payments…</p> : purchases.length === 0 ? (
          <p className="state">No package payment submissions yet.</p>
        ) : (
          <div className="admin-package-items">
            {purchases.map((purchase) => (
              <article className="admin-package-item" key={purchase.id}>
                <div className="admin-package-user"><strong>{purchase.user_name}</strong><span>{purchase.user_email}</span></div>
                <div className="admin-package-summary"><strong>{purchase.package_name} · {money(purchase.amount, purchase.currency)}{purchase.payment_amount_bdt && <> · BDT {Number(purchase.payment_amount_bdt).toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</>}</strong><span>{purchase.payment_method} · Ref: <b>{purchase.payment_reference}</b>{purchase.usd_bdt_rate && <> · Rate: 1 USD = BDT {Number(purchase.usd_bdt_rate).toLocaleString("en-BD")}</>}</span><time dateTime={purchase.created_at}>{new Date(purchase.created_at).toLocaleString()}</time></div>
                <Badge className={`withdrawal-status withdrawal-${purchase.status.toLowerCase()}`} variant="outline">{purchase.status.toLowerCase()}</Badge>
                {purchase.admin_note && <p className="admin-package-note">{purchase.admin_note}</p>}
                {purchase.status === "PENDING" && (
                  <div className="admin-package-actions">
                    <Button className="primary" type="button" disabled={busyId === purchase.id} onClick={() => void review(purchase, "approve")}><Check size={15} /> Approve & unlock</Button>
                    <Button className="secondary-button is-danger" variant="destructive" type="button" disabled={busyId === purchase.id} onClick={() => void review(purchase, "reject")}><X size={15} /> Reject</Button>
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </Card>
    </main>
  );
}
