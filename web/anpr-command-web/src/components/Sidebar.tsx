"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const ROUTES = [
  { href: "/", label: "Command Centre", icon: "◈", desc: "Live monitoring & map" },
  { href: "/trajectory", label: "Trajectory", icon: "⤳", desc: "Vehicle path tracking" },
  { href: "/review", label: "Review Queue", icon: "◎", desc: "OCR manual validation" },
  { href: "/alerts", label: "Alerts & Watchlist", icon: "▲", desc: "Hotlisted vehicles" },
  { href: "/analytics", label: "Analytics", icon: "▤", desc: "Heatmaps & flow rates" },
  { href: "/system", label: "System Health", icon: "◫", desc: "Camera edge status" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-full w-60 flex-col border-r border-[var(--border)] bg-[var(--surface)] select-none">
      {/* Brand Header */}
      <div className="flex h-16 items-center gap-3 px-4 border-b border-[var(--border)] bg-[var(--panel)]">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[var(--signal)] font-mono font-bold text-xs text-black shadow-md shadow-[var(--signal)]/20">
          TR
        </div>
        <div>
          <div className="font-display text-sm font-bold tracking-wide text-[var(--text)]">
            TRACE-SIH
          </div>
          <div className="text-[10px] text-[var(--signal)] font-mono uppercase tracking-wider">
            ANPR COMMAND
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 py-4 px-2 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--muted)]">
          Navigation
        </div>
        {ROUTES.map((r) => {
          const active = pathname === r.href;
          return (
            <Link
              key={r.href}
              href={r.href}
              className={`group flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                active
                  ? "bg-[var(--signal)]/15 text-[var(--signal)] border border-[var(--signal)]/30 shadow-sm"
                  : "text-[var(--muted)] hover:text-[var(--text)] hover:bg-white/5"
              }`}
            >
              <span
                className={`w-6 text-center text-sm font-mono transition-transform group-hover:scale-110 ${
                  active ? "text-[var(--signal)] font-bold" : "text-[var(--muted)]"
                }`}
              >
                {r.icon}
              </span>
              <div className="flex flex-col">
                <span className={`leading-tight ${active ? "font-semibold text-white" : ""}`}>
                  {r.label}
                </span>
                <span className="text-[9px] text-[var(--muted)] group-hover:text-[var(--text)]/70">
                  {r.desc}
                </span>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-3.5 border-t border-[var(--border)] bg-[var(--panel)]">
        <div className="flex items-center justify-between text-[10px] text-[var(--muted)]">
          <span>Bengaluru Grid</span>
          <span className="font-mono text-[var(--signal)]">v1.0 Live</span>
        </div>
      </div>
    </aside>
  );
}
