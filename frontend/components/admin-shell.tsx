"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Banknote, ImagePlus, LayoutDashboard, LogOut, Menu, ShieldCheck, X } from "lucide-react";
import { api } from "../lib/api";
import { Avatar, AvatarFallback } from "./ui/avatar";
import { Button } from "./ui/button";

type AdminIdentity = {
  full_name: string;
  email: string;
};

const navigation = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard },
  { href: "/admin/withdrawals", label: "Manual withdrawals", icon: Banknote },
  { href: "/admin/banners", label: "Dashboard banners", icon: ImagePlus },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname().replace(/\/+$/, "") || "/";
  const [identity, setIdentity] = useState<AdminIdentity | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  useEffect(() => {
    if (pathname === "/admin/login") return;
    api<AdminIdentity>("/auth/me")
      .then(setIdentity)
      .catch(() => {
        setIdentity(null);
      });
  }, [pathname]);

  async function logout() {
    setLoggingOut(true);
    setLogoutError("");
    try {
      await api<void>("/auth/logout", { method: "POST" });
      window.location.assign("/admin/login");
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "Unable to sign out.");
      setLoggingOut(false);
    }
  }

  const initials = identity?.full_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");

  if (pathname === "/admin/login") return <>{children}</>;

  return (
    <main className="app-shell admin-app-shell">
      <Button
        className="mobile-menu-toggle"
        variant="ghost"
        size="icon"
        type="button"
        aria-label={menuOpen ? "Close admin navigation" : "Open admin navigation"}
        aria-expanded={menuOpen}
        aria-controls="admin-navigation"
        onClick={() => setMenuOpen((open) => !open)}
      >
        <span aria-hidden="true">{menuOpen ? <X /> : <Menu />}</span>
      </Button>
      {menuOpen && (
        <Button
          className="mobile-menu-backdrop"
          variant="ghost"
          type="button"
          aria-label="Close admin navigation"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside className={`app-sidebar admin-sidebar${menuOpen ? " is-open" : ""}`}>
        <Link className="brand" href="/admin" onClick={() => setMenuOpen(false)}>
          <i aria-hidden="true">W</i> WorkBit
        </Link>
        <p className="tagline">Platform operations</p>
        <p className="nav-caption">ADMIN CONSOLE</p>
        <nav id="admin-navigation" aria-label="Admin navigation">
          {navigation.map((item) => {
            const active = pathname === item.href ||
              (item.href !== "/admin" && pathname.startsWith(`${item.href}/`));
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
        <Link className="admin-user-space-link" href="/dashboard">
          <span className="nav-icon" aria-hidden="true"><ShieldCheck size={17} /></span>
          User dashboard
        </Link>
        <div className="sidebar-spacer" />
        {logoutError && <p className="logout-error" role="alert">{logoutError}</p>}
        <div className="sidebar-account">
          <Avatar className="user-avatar" aria-hidden="true">
            <AvatarFallback>{initials || "AD"}</AvatarFallback>
          </Avatar>
          <span className="sidebar-user-copy">
            <strong>{identity?.full_name || "Admin account"}</strong>
            <small>Administrator</small>
          </span>
          <Button
            className="logout-button"
            variant="ghost"
            size="icon"
            onClick={() => void logout()}
            disabled={loggingOut}
            type="button"
            aria-label={loggingOut ? "Signing out" : "Sign out"}
          >
            {loggingOut ? <span aria-hidden="true">…</span> : <LogOut size={16} />}
          </Button>
        </div>
      </aside>
      <section className="app-content admin-app-content">{children}</section>
    </main>
  );
}
