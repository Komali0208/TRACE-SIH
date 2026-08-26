"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useDataMode } from "@/lib/mode";

const NAV_TABS = [
  { href: "/", label: "Dashboard" },
  { href: "/trajectory", label: "Trajectory" },
  { href: "/review", label: "Review" },
  { href: "/alerts", label: "Alerts" },
  { href: "/analytics", label: "Analytics" },
  { href: "/system", label: "System" },
];

export function TopBar() {
  const { mode } = useDataMode();
  const pathname = usePathname();

  return (
    <header className="h-14 shrink-0 flex items-center justify-between px-6 border-b border-[var(--border)] bg-[var(--surface)]/90 backdrop-blur sticky top-0 z-30">
      {/* Quick Navigation Tabs */}
      <div className="flex items-center gap-1.5">
        {NAV_TABS.map((tab) => {
          const active = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                active
                  ? "bg-[var(--signal)] text-black font-semibold shadow-sm"
                  : "text-[var(--muted)] hover:text-[var(--text)] hover:bg-white/5"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>

      {/* Grid Meta & Status Indicator */}
      <div className="flex items-center gap-3">
        <span className="hidden sm:inline-block text-[11px] text-[var(--muted)] font-mono">
          8 Cameras Online
        </span>
        {mode === "checking" && (
          <span className="text-[11px] text-[var(--muted)] flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-white/10 bg-white/5">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--muted)] animate-pulse" />
            Connecting
          </span>
        )}
        {mode === "live" && (
          <span className="text-[11px] font-semibold text-[var(--ok)] flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[var(--ok)]/30 bg-[var(--ok)]/10 font-mono">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--ok)] animate-pulseMarker" />
            LIVE FEED
          </span>
        )}
        {mode === "cached" && (
          <span
            className="text-[11px] font-semibold text-[var(--warn)] flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[var(--warn)]/30 bg-[var(--warn)]/10 font-mono"
            title="Live backend unavailable — showing cached dataset."
          >
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--warn)]" />
            CACHED
          </span>
        )}
      </div>
    </header>
  );
}
