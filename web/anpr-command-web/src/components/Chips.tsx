"use client";
import { FLAG_LABEL } from "@/lib/types";
import { confColor } from "@/lib/utils";

export function FlagChip({ flag }: { flag: string }) {
  const danger = flag === "SPEED_ANOMALY" || flag === "UNREADABLE";
  const color = danger ? "var(--danger)" : "var(--warn)";
  return (
    <span
      className="eyebrow inline-flex items-center rounded px-1.5 py-0.5 border"
      style={{ color, borderColor: `${color}55`, background: `${color}18` }}
    >
      {FLAG_LABEL[flag] ?? flag}
    </span>
  );
}

export function ConfidenceBar({ value, width = 64 }: { value: number; width?: number }) {
  const color = confColor(value);
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 rounded-full bg-[var(--surface-2)] overflow-hidden" style={{ width }}>
        <div className="h-full rounded-full" style={{ width: `${Math.round(value * 100)}%`, background: color }} />
      </div>
      <span className="font-data text-[11px]" style={{ color }}>
        {(value * 100).toFixed(0)}%
      </span>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    stolen: "var(--danger)",
    blacklisted: "var(--danger)",
    flagged: "var(--warn)",
  };
  const color = map[status] ?? "var(--signal)";
  return (
    <span
      className="eyebrow inline-flex items-center rounded-full px-2 py-0.5 border"
      style={{ color, borderColor: `${color}55`, background: `${color}18` }}
    >
      {status}
    </span>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-[var(--surface-2)] ${className}`} />;
}
