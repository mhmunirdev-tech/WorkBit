"use client";

import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { RefreshCw, Search, Users, WalletCards } from "lucide-react";
import { api } from "../lib/api";
import { formatUsd } from "../lib/utils";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";

type AdminUser = {
  id: string;
  full_name: string;
  email: string;
  country: string;
  phone_number: string | null;
  status: string;
  email_verified: boolean;
  created_at: string;
  available_balance: string;
  pending_balance: string;
  lifetime_earned: string;
  lifetime_withdrawn: string;
  currency: string;
  active_package: boolean;
  package_expires_at: string | null;
};

type AdminUserResponse = {
  items: AdminUser[];
  total: number;
  registered_count: number;
  page: number;
  page_size: number;
  active_count: number;
  pending_verification_count: number;
  suspended_count: number;
  active_package_count: number;
  total_wallet_balance: string;
};

const PAGE_SIZE = 25;

function statusLabel(status: string) {
  return status.toLowerCase().replaceAll("_", " ");
}

function UserStatus({ user }: { user: AdminUser }) {
  const className = `user-registry-status status-${user.status.toLowerCase()}`;
  return <Badge className={className} variant="outline">{statusLabel(user.status)}</Badge>;
}

export function AdminUsers() {
  const [data, setData] = useState<AdminUserResponse | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("ALL");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [appliedStatus, setAppliedStatus] = useState("ALL");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    if (appliedSearch) query.set("search", appliedSearch);
    if (appliedStatus !== "ALL") query.set("status", appliedStatus);
    try {
      setData(await api<AdminUserResponse>(`/admin/users?${query.toString()}`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "User records could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [appliedSearch, appliedStatus, page]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setAppliedSearch(search.trim());
    setAppliedStatus(status);
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <main className="admin-users-page">
      <header className="admin-withdrawals-header admin-users-header">
        <div>
          <p className="eyebrow">ACCOUNT OPERATIONS</p>
          <h1>User registry</h1>
          <p>Inspect registered user status, verification, package access and wallet balances from one source of truth.</p>
        </div>
        <div className="admin-withdrawals-links">
          <Button className="secondary-button" variant="outline" type="button" onClick={() => void refresh()} disabled={loading}>
            <RefreshCw size={15} /> Refresh
          </Button>
        </div>
      </header>

      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}

      <section className="admin-user-summary" aria-label="User summary">
        <Card className="admin-user-summary-card"><Users size={17} /><span><small>Registered users</small><strong>{data?.registered_count.toLocaleString() ?? "—"}</strong></span></Card>
        <Card className="admin-user-summary-card"><span><small>Active accounts</small><strong>{data?.active_count.toLocaleString() ?? "—"}</strong></span></Card>
        <Card className="admin-user-summary-card"><span><small>Pending verification</small><strong>{data?.pending_verification_count.toLocaleString() ?? "—"}</strong></span></Card>
        <Card className="admin-user-summary-card"><WalletCards size={17} /><span><small>Active packages</small><strong>{data?.active_package_count.toLocaleString() ?? "—"}</strong></span></Card>
        <Card className="admin-user-summary-card"><span><small>User wallet balance</small><strong>{data ? formatUsd(data.total_wallet_balance) : "—"}</strong></span></Card>
      </section>

      <Card className="admin-user-registry-card">
        <form className="admin-user-filters" onSubmit={submit}>
          <label><span>Search name, email or phone</span><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="e.g. user@example.com" /></label>
          <label><span>Status</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="ALL">All statuses</option><option value="ACTIVE">Active</option><option value="PENDING_VERIFICATION">Pending verification</option><option value="PENDING_REVIEW">Pending review</option><option value="SUSPENDED">Suspended</option><option value="BANNED">Banned</option></select></label>
          <Button className="primary" type="submit"><Search size={15} /> Search</Button>
        </form>

        {loading ? <p className="state" role="status">Loading user records…</p> : data?.items.length ? (
          <div className="admin-user-table-wrap">
            <table className="admin-user-table">
              <thead><tr><th>User</th><th>Status</th><th>Joined</th><th>Package</th><th>Available</th><th>Lifetime earned</th><th>Withdrawn</th></tr></thead>
              <tbody>{data.items.map((user) => (
                <tr key={user.id}>
                  <td><strong>{user.full_name}</strong><span>{user.email}</span><small>{user.country}{user.phone_number ? ` · ${user.phone_number}` : ""}</small></td>
                  <td><UserStatus user={user} /><small className={user.email_verified ? "user-verified" : "user-unverified"}>{user.email_verified ? "Email verified" : "Email not verified"}</small></td>
                  <td><time dateTime={user.created_at}>{new Date(user.created_at).toLocaleDateString()}</time></td>
                  <td>{user.active_package ? <><strong className="user-package-active">Active</strong><small>Until {user.package_expires_at ? new Date(user.package_expires_at).toLocaleDateString() : "—"}</small></> : <span className="user-package-none">None</span>}</td>
                  <td><strong>{formatUsd(user.available_balance)}</strong><small>Pending {formatUsd(user.pending_balance)}</small></td>
                  <td>{formatUsd(user.lifetime_earned)}</td>
                  <td>{formatUsd(user.lifetime_withdrawn)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <p className="state">No users match the current filters.</p>}

        <footer className="admin-user-pagination">
          <span>{data ? `Showing ${data.items.length} of ${data.total} users` : ""}</span>
          <div><Button variant="outline" type="button" disabled={page <= 1 || loading} onClick={() => setPage((current) => current - 1)}>Previous</Button><strong>Page {page} of {totalPages}</strong><Button variant="outline" type="button" disabled={page >= totalPages || loading} onClick={() => setPage((current) => current + 1)}>Next</Button></div>
        </footer>
      </Card>
    </main>
  );
}
