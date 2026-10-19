"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ArrowUpRight, Check, PackageCheck, RefreshCw, Save } from "lucide-react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";

type EarningPackage = {
  code: string;
  name: string;
  description: string;
  amount: string;
  currency: string;
  duration_days: number;
  is_active: boolean;
  sort_order: number;
};

type PackageForm = {
  name: string;
  description: string;
  amount: string;
  duration_days: string;
  is_active: boolean;
  sort_order: string;
};

function toForm(item: EarningPackage): PackageForm {
  return {
    name: item.name,
    description: item.description,
    amount: item.amount,
    duration_days: String(item.duration_days),
    is_active: item.is_active,
    sort_order: String(item.sort_order),
  };
}

export function AdminEarningPackages() {
  const [packages, setPackages] = useState<EarningPackage[]>([]);
  const [forms, setForms] = useState<Record<string, PackageForm>>({});
  const [loading, setLoading] = useState(true);
  const [savingCode, setSavingCode] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadPackages = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api<EarningPackage[]>("/admin/packages");
      setPackages(result);
      setForms(Object.fromEntries(result.map((item) => [item.code, toForm(item)])));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Earning packages could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPackages();
  }, [loadPackages]);

  function updateForm(code: string, field: keyof PackageForm, value: string | boolean) {
    setForms((current) => ({
      ...current,
      [code]: { ...current[code], [field]: value },
    }));
  }

  async function savePackage(event: FormEvent<HTMLFormElement>, item: EarningPackage) {
    event.preventDefault();
    const form = forms[item.code];
    if (!form) return;
    setSavingCode(item.code);
    setError("");
    setNotice("");
    try {
      const updated = await api<EarningPackage>(`/admin/packages/${item.code}`, {
        method: "PUT",
        body: JSON.stringify({
          ...form,
          amount: form.amount,
          duration_days: Number(form.duration_days),
          sort_order: Number(form.sort_order),
        }),
      });
      setPackages((current) => current.map((entry) => entry.code === updated.code ? updated : entry));
      setForms((current) => ({ ...current, [updated.code]: toForm(updated) }));
      const updateMessage = `${updated.name} package updated.`;
      setNotice(updateMessage);
      showToast({ title: "Package updated", description: updateMessage, variant: "success" });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The package could not be updated.");
    } finally {
      setSavingCode("");
    }
  }

  return (
    <main className="admin-earning-packages-page">
      <header className="admin-withdrawals-header">
        <div>
          <p className="eyebrow">PRODUCT CATALOG</p>
          <h1>Earning packages</h1>
          <p>Edit the public package title, description, price, access period, visibility, and order.</p>
        </div>
        <div className="admin-withdrawals-links">
          <Button className="secondary-button" variant="outline" type="button" onClick={() => void loadPackages()} disabled={loading}>
            <RefreshCw size={15} /> Refresh
          </Button>
          <Button variant="link" asChild>
            <Link href="/admin">Admin overview <ArrowUpRight size={14} /></Link>
          </Button>
        </div>
      </header>

      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      {notice && <Alert className="state" role="status"><AlertDescription>{notice}</AlertDescription></Alert>}
      <Alert className="package-admin-notice" role="note">
        <AlertDescription>
          Changes apply to new purchases and the public catalog. Existing active package expiry dates and pending purchase prices remain unchanged.
        </AlertDescription>
      </Alert>

      {loading ? (
        <Card className="panel admin-package-list" aria-busy="true">Loading package settings…</Card>
      ) : error && packages.length === 0 ? (
        <Card className="panel admin-package-list" role="status">Package data is unavailable until the database request succeeds.</Card>
      ) : packages.length === 0 ? (
        <Card className="panel admin-package-list">No earning packages were found.</Card>
      ) : (
        <section className="admin-earning-package-grid" aria-label="Manage earning packages">
          {packages.map((item) => {
            const form = forms[item.code];
            if (!form) return null;
            return (
              <Card className="admin-earning-package-card" key={item.code}>
                <header className="admin-earning-package-heading">
                  <span className="admin-earning-package-icon"><PackageCheck size={19} /></span>
                  <div><p className="eyebrow">{item.code}</p><h2>{item.name}</h2></div>
                  <Badge variant="outline" className={form.is_active ? "package-active-badge" : "package-inactive-badge"}>
                    {form.is_active ? "Visible" : "Hidden"}
                  </Badge>
                </header>
                <form className="admin-earning-package-form" onSubmit={(event) => void savePackage(event, item)}>
                  <label>Package title
                    <Input value={form.name} onChange={(event) => updateForm(item.code, "name", event.target.value)} required maxLength={80} />
                  </label>
                  <label>Description
                    <Textarea value={form.description} onChange={(event) => updateForm(item.code, "description", event.target.value)} maxLength={1000} rows={3} />
                  </label>
                  <div className="admin-earning-package-fields">
                    <label>Price ({item.currency})
                      <Input type="number" value={form.amount} onChange={(event) => updateForm(item.code, "amount", event.target.value)} min="0.01" step="0.01" required />
                    </label>
                    <label>Access duration (days)
                      <Input type="number" value={form.duration_days} onChange={(event) => updateForm(item.code, "duration_days", event.target.value)} min="1" max="36500" step="1" required />
                    </label>
                  </div>
                  <div className="admin-earning-package-fields">
                    <label>Display order
                      <Input type="number" value={form.sort_order} onChange={(event) => updateForm(item.code, "sort_order", event.target.value)} min="0" max="10000" step="1" required />
                    </label>
                    <label className="admin-package-visibility">
                      <input type="checkbox" checked={form.is_active} onChange={(event) => updateForm(item.code, "is_active", event.target.checked)} />
                      Show on website and allow purchases
                    </label>
                  </div>
                  <Button className="primary admin-package-save" type="submit" disabled={savingCode !== ""}>
                    {savingCode === item.code ? <RefreshCw size={15} /> : <Save size={15} />}
                    {savingCode === item.code ? "Saving…" : "Save package"}
                    {savingCode !== item.code && <Check size={15} />}
                  </Button>
                </form>
              </Card>
            );
          })}
        </section>
      )}
    </main>
  );
}
