"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import {
  BarChart3,
  FileText,
  LayoutDashboard,
  MessageCircleQuestion,
  Sparkles,
  Users,
} from "lucide-react";
import { UserMenu } from "@/components/auth/UserMenu";

type AppShellProps = {
  children: React.ReactNode;
};

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/meeting-room", label: "Meeting Room", icon: Users, comingSoon: true },
  { href: "/group-interview", label: "Group Interview", icon: Users },
  { href: "/pre-interview", label: "Interview", icon: MessageCircleQuestion },
  { href: "/resume", label: "Resume", icon: FileText },
  { href: "/results", label: "Results", icon: BarChart3 },
];

const shellRoutes = new Set([
  "/dashboard",
  "/meeting-room", "/resume",
  "/group-interview",
  "/interview",
  "/results",
  "/home",
]);

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const [showComingSoonToast, setShowComingSoonToast] = useState(false);
  const toastTimerRef = useRef<number | null>(null);

  const handleComingSoonClick = () => {
    setShowComingSoonToast(true);
    if (toastTimerRef.current !== null) {
      window.clearTimeout(toastTimerRef.current);
    }
    toastTimerRef.current = window.setTimeout(() => {
      setShowComingSoonToast(false);
      toastTimerRef.current = null;
    }, 3200);
  };

  useEffect(() => {
    return () => {
      if (toastTimerRef.current !== null) {
        window.clearTimeout(toastTimerRef.current);
      }
    };
  }, []);

  const shouldShowShell = shellRoutes.has(pathname);
  if (!shouldShowShell) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-[var(--app-bg)] text-[var(--app-fg)]">
      <div className="relative flex w-full">
        {/* ── Desktop Sidebar ─────────────────────────────── */}
        <aside className="sticky top-0 hidden h-screen w-60 shrink-0 border-r border-[var(--border-default)] bg-white/70 px-5 py-7 backdrop-blur-2xl lg:flex lg:flex-col">
          <div>
            <p className="font-display font-extrabold text-2xl tracking-tight text-[var(--text-primary)]">
              evalvate
            </p>
            <h1 className="mt-3 text-lg font-bold text-[var(--text-primary)]">
              Interview Studio
            </h1>
            <p className="mt-1.5 text-xs text-[var(--text-tertiary)]">
              Practice, reflect, improve.
            </p>
          </div>

          <nav className="mt-8 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              const sharedClassName = clsx(
                "flex items-center gap-2.5 rounded-xl border px-3.5 py-2.5 text-[13px] font-medium transition-all duration-200",
                active
                  ? "border-[var(--accent-primary)]/20 bg-[var(--accent-primary)]/8 text-[var(--accent-primary)] shadow-sm"
                  : "border-transparent text-[var(--text-secondary)] hover:border-[var(--border-default)] hover:bg-[var(--surface-secondary)] hover:text-[var(--text-primary)]"
              );

              if (item.comingSoon) {
                return (
                  <button
                    key={item.href}
                    type="button"
                    onClick={handleComingSoonClick}
                    className={clsx("w-full", sharedClassName)}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                    <span className="ml-auto rounded-full bg-[var(--accent-primary)]/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--accent-primary)]">
                      Soon
                    </span>
                  </button>
                );
              }

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={clsx(
                    "flex items-center gap-2.5 rounded-xl border px-3.5 py-2.5 text-[13px] font-medium transition-all duration-200",
                    active
                      ? "border-[var(--accent-primary)]/20 bg-[var(--accent-primary)]/8 text-[var(--accent-primary)] shadow-sm"
                      : "border-transparent text-[var(--text-secondary)] hover:border-[var(--border-default)] hover:bg-[var(--surface-secondary)] hover:text-[var(--text-primary)]"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-secondary)] p-3.5 text-xs text-[var(--text-tertiary)] leading-relaxed">
            One thoughtful interview at a time. Keep your momentum going.
          </div>
          <UserMenu />
        </aside>

        {/* ── Main Content ────────────────────────────────── */}
        <main className="w-full px-4 pb-24 pt-6 sm:px-6 lg:px-8 lg:pb-8 lg:pt-8">
          {children}
        </main>
      </div>

      {/* ── Mobile Bottom Nav ─────────────────────────────── */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-[var(--border-default)] bg-white/85 px-3 py-2 backdrop-blur-2xl lg:hidden">
        <div
          className="mx-auto grid max-w-xl gap-1"
          style={{
            gridTemplateColumns: `repeat(${navItems.length}, minmax(0, 1fr))`,
          }}
        >
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            const mobileClassName = clsx(
              "flex flex-col items-center justify-center rounded-lg px-2 py-2 text-[11px] font-medium transition-all",
              active ? "bg-[var(--accent-primary)]/8 text-[var(--accent-primary)]" : "text-[var(--text-tertiary)] hover:bg-[var(--surface-secondary)] hover:text-[var(--text-secondary)]"
            );

            if (item.comingSoon) {
              return (
                <button
                  key={item.href}
                  type="button"
                  onClick={handleComingSoonClick}
                  className={mobileClassName}
                >
                  <Icon className="mb-1 h-4 w-4" />
                  {item.label}
                </button>
              );
            }

            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex flex-col items-center justify-center rounded-lg px-2 py-2 text-[11px] font-medium transition-all",
                  active
                    ? "bg-[var(--accent-primary)]/8 text-[var(--accent-primary)]"
                    : "text-[var(--text-tertiary)] hover:bg-[var(--surface-secondary)] hover:text-[var(--text-secondary)]"
                )}
              >
                <Icon className="mb-1 h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>

      {showComingSoonToast ? (
        <div className="fixed bottom-20 left-1/2 z-50 -translate-x-1/2 lg:bottom-8">
          <div className="flex items-center gap-2.5 rounded-2xl border border-[var(--border-default)] bg-[var(--surface-primary)] px-4 py-3 shadow-2xl">
            <Sparkles className="h-4 w-4 text-[var(--accent-primary)]" />
            <p className="text-sm font-medium text-[var(--text-primary)]">
              Team Interview feature is coming soon. Stay tuned!
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
