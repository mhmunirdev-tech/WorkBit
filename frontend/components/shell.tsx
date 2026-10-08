"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowDownUp,
  Banknote,
  Gift,
  History,
  Home,
  Link2,
  LogOut,
  Menu,
  Settings,
  Sparkles,
  UserRound,
  Wallet,
  X,
} from "lucide-react";
import { api } from "../lib/api";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Button } from "./ui/button";

export type ShellUser = {
  full_name: string;
  email: string;
  status: string;
  email_verified: boolean;
  avatar_url?: string | null;
};

const pageTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/offers": "Explore offers",
  "/referrals": "Referrals",
  "/wallet": "Wallet",
  "/transactions": "Transactions",
  "/withdraw": "Withdraw",
  "/withdrawals": "Withdrawal history",
  "/rewards": "Reward history",
  "/profile": "Profile",
  "/settings": "Settings",
};

const navigation = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/offers", label: "Explore offers", icon: Sparkles },
  { href: "/referrals", label: "Referrals", icon: Link2 },
  { href: "/wallet", label: "Wallet", icon: Wallet },
  { href: "/transactions", label: "Transactions", icon: ArrowDownUp },
  { href: "/withdraw", label: "Withdraw", icon: Banknote },
  { href: "/withdrawals", label: "Withdrawal history", icon: History },
  { href: "/rewards", label: "Reward history", icon: Gift },
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Shell({
  children,
  user,
}: {
  children: React.ReactNode;
  user?: ShellUser | null;
}) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const [fetchedUser, setFetchedUser] = useState<ShellUser | null>(null);
  const displayUser = user ?? fetchedUser;
  const initials = displayUser?.full_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
  const pageTitle =
    pageTitles[pathname] ??
    (pathname.startsWith("/offers/") ? "Offer details" : "WorkBit");

  useEffect(() => {
    if (user) {
      setFetchedUser(user);
      return;
    }
    let active = true;
    api<ShellUser>("/auth/me")
      .then((account) => {
        if (active) setFetchedUser(account);
      })
      .catch(() => {
        if (active) setFetchedUser(null);
      });
    return () => {
      active = false;
    };
  }, [user]);

  async function logout() {
    setLoggingOut(true);
    setLogoutError("");
    try {
      await api<void>("/auth/logout", { method: "POST" });
      window.location.assign("/login");
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "Unable to sign out.");
      setLoggingOut(false);
    }
  }

  return (
    <main className="app-shell">
      <Button
        className="mobile-menu-toggle"
        variant="ghost"
        size="icon"
        type="button"
        aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
        aria-expanded={menuOpen}
        aria-controls="dashboard-navigation"
        onClick={() => setMenuOpen((open) => !open)}
      >
        <span aria-hidden="true">{menuOpen ? <X /> : <Menu />}</span>
      </Button>
      {menuOpen && (
        <Button
          className="mobile-menu-backdrop"
          variant="ghost"
          type="button"
          aria-label="Close navigation menu"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside className={`app-sidebar${menuOpen ? " is-open" : ""}`}>
        <Link className="brand" href="/dashboard" onClick={() => setMenuOpen(false)}>
          <i aria-hidden="true">W</i> WorkBit
        </Link>
        <p className="tagline">Work. Complete. Earn.</p>
        <p className="nav-caption">YOUR SPACE</p>
        <nav id="dashboard-navigation" aria-label="Main navigation">
          {navigation.map((item) => {
            const active =
              pathname === item.href ||
              (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
            return (
              <Link
                className={`app-nav-link${active ? " is-active" : ""}`}
                href={item.href}
                aria-current={active ? "page" : undefined}
                key={item.href}
                onClick={() => setMenuOpen(false)}
              >
                <span className="nav-icon" aria-hidden="true"><item.icon size={17} /></span>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-spacer" />
        {logoutError && <p className="logout-error" role="alert">{logoutError}</p>}
        <div className="sidebar-account">
          <Avatar className="user-avatar" aria-hidden="true">
            {displayUser?.avatar_url && <AvatarImage src={displayUser.avatar_url} alt="" />}
            <AvatarFallback>{initials || "WB"}</AvatarFallback>
          </Avatar>
          <span className="sidebar-user-copy">
            <strong>{displayUser?.full_name || "Your account"}</strong>
            <small>{displayUser?.status?.replaceAll("_", " ") || "Member"}</small>
          </span>
          <Button className="logout-button" variant="ghost" size="icon" onClick={logout} disabled={loggingOut} type="button" aria-label={loggingOut ? "Signing out" : "Sign out"}>
            {loggingOut ? <span aria-hidden="true">…</span> : <LogOut size={16} />}
          </Button>
        </div>
      </aside>
      <section className="app-content">
        <header className="dashboard-topbar">
          <div className="dashboard-topbar-title">
            <p className="eyebrow">WORKBIT / MY SPACE</p>
            <h2>{pageTitle}</h2>
          </div>
          <Link className="dashboard-topbar-user" href="/profile">
            <Avatar className="dashboard-topbar-avatar" aria-hidden="true">
              {displayUser?.avatar_url && <AvatarImage src={displayUser.avatar_url} alt="" />}
              <AvatarFallback>{initials || "WB"}</AvatarFallback>
            </Avatar>
            <span>
              <strong>{displayUser?.full_name || "Your account"}</strong>
              <small>View profile</small>
            </span>
          </Link>
        </header>
        {children}
      </section>
    </main>
  );
}
