"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useRef, useState } from "react";
import { ArrowRight } from "lucide-react";
import { formatUsd } from "../lib/utils";
import {
  Award,
  Gift,
  Home,
  LogOut,
  Menu,
  PackageCheck,
  Settings,
  Sparkles,
  UserRound,
  Wallet,
  X,
} from "lucide-react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Button } from "./ui/button";

export type ShellUser = {
  full_name: string;
  email: string;
  country?: string;
  status: string;
  email_verified: boolean;
  avatar_url?: string | null;
};

const ShellUserContext = createContext<ShellUser | null>(null);

export function useShellUser(): ShellUser | null {
  return useContext(ShellUserContext);
}

type WalletSnapshot = {
  available_balance: string | number;
  currency: string;
};

const pageTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/offers": "Explore offers",
  "/packages": "Earning packages",
  "/ranks": "Ranks",
  "/wallet": "Wallet",
  "/transactions": "Transactions",
  "/rewards": "Reward history",
  "/profile": "Profile",
  "/settings": "Settings",
};

const navigation = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/offers", label: "Explore offers", icon: Sparkles },
  { href: "/packages", label: "Earning packages", icon: PackageCheck },
  { href: "/ranks", label: "Ranks", icon: Award },
  { href: "/wallet", label: "Wallet", icon: Wallet },
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
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [fetchedUser, setFetchedUser] = useState<ShellUser | null>(null);
  const [wallet, setWallet] = useState<WalletSnapshot | null>(null);
  const [walletLoadError, setWalletLoadError] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);
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
  const availableBalance = wallet
    ? formatUsd(wallet.available_balance)
    : null;

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

  useEffect(() => {
    let active = true;
    api<WalletSnapshot>("/wallet")
      .then((snapshot) => {
        if (active) {
          setWallet(snapshot);
          setWalletLoadError(false);
        }
      })
      .catch(() => {
        if (active) {
          setWallet(null);
          setWalletLoadError(true);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!accountMenuOpen) return;

    function closeOnOutsideClick(event: MouseEvent) {
      if (event.target instanceof Node && !accountMenuRef.current?.contains(event.target)) {
        setAccountMenuOpen(false);
      }
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setAccountMenuOpen(false);
    }

    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [accountMenuOpen]);

  async function logout() {
    setLoggingOut(true);
    setLogoutError("");
    setAccountMenuOpen(false);
    try {
      await api<void>("/auth/logout", { method: "POST" });
      showToast({ title: "Signed out", description: "You have been signed out.", variant: "success" });
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
            const icon = <span className="nav-icon" aria-hidden="true"><item.icon size={17} /></span>;
            return (
              <Link
                className={`app-nav-link${active ? " is-active" : ""}`}
                href={item.href}
                aria-current={active ? "page" : undefined}
                key={item.href}
                onClick={() => setMenuOpen(false)}
              >
                {icon}
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
            <Link className="dashboard-mobile-brand" href="/dashboard" aria-label="WorkBit home">
              <i aria-hidden="true">W</i> WorkBit
            </Link>
          </div>
          <div className="dashboard-topbar-actions">
            <Link
              className={`dashboard-wallet-balance${walletLoadError ? " is-unavailable" : ""}`}
              href="/wallet"
              aria-label={wallet ? `Available balance ${availableBalance}. Open wallet.` : walletLoadError ? "Balance unavailable. Open wallet." : "Loading available balance."}
            >
              <span className="dashboard-wallet-icon"><Wallet size={18} aria-hidden="true" /></span>
              <span className="dashboard-wallet-copy">
                <small>Available balance</small>
                <strong>{availableBalance ?? (walletLoadError ? "Unavailable" : "Loading…")}</strong>
              </span>
              <ArrowRight className="dashboard-wallet-arrow" size={14} aria-hidden="true" />
            </Link>
            <div className="dashboard-account-menu" ref={accountMenuRef}>
              <button
                className="dashboard-account-trigger"
                type="button"
                aria-label="Open account menu"
                aria-expanded={accountMenuOpen}
                aria-controls="dashboard-account-dropdown"
                onClick={() => setAccountMenuOpen((open) => !open)}
              >
                <span
                  className={`dashboard-avatar-wrap${displayUser?.status ? ` status-${displayUser.status.toLowerCase()}` : ""}`}
                  title={displayUser?.status ? `Account status: ${displayUser.status.replaceAll("_", " ")}` : undefined}
                >
                  <Avatar className="dashboard-topbar-avatar">
                    {displayUser?.avatar_url && <AvatarImage src={displayUser.avatar_url} alt="" />}
                    <AvatarFallback>{initials || "WB"}</AvatarFallback>
                  </Avatar>
                  {displayUser?.status && (
                    <span
                      className="dashboard-avatar-status"
                      role="img"
                      aria-label={`Account status: ${displayUser.status.replaceAll("_", " ")}`}
                    />
                  )}
                </span>
              </button>
              {accountMenuOpen && (
                <div className="dashboard-account-dropdown" id="dashboard-account-dropdown" aria-label="Account menu">
                  <div className="dashboard-account-identity">
                    <strong>{displayUser?.full_name || "Your account"}</strong>
                    <span>{displayUser?.email || "Email unavailable"}</span>
                  </div>
                  <Link href="/profile" onClick={() => setAccountMenuOpen(false)}>View profile</Link>
                  <Link href="/settings" onClick={() => setAccountMenuOpen(false)}>Account settings</Link>
                  <button type="button" onClick={() => void logout()} disabled={loggingOut}>
                    {loggingOut ? "Signing out…" : "Sign out"}
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>
        <ShellUserContext.Provider value={displayUser}>
          {children}
        </ShellUserContext.Provider>
      </section>
    </main>
  );
}
