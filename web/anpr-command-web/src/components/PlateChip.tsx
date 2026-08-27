"use client";

import { useRegistry } from "@/lib/registry-context";

export function PlateChip({
  plate,
  size = "md",
  commercial = false,
  className = "",
  interactive = true,
}: {
  plate: string | null | undefined;
  size?: "sm" | "md" | "lg";
  commercial?: boolean;
  className?: string;
  /** When false, chip is display-only (e.g. inside the registry panel header). */
  interactive?: boolean;
}) {
  const { openRegistry } = useRegistry();
  const unreadable = !plate;
  const dims =
    size === "sm"
      ? "h-6 min-w-[92px] text-[11px] px-1.5"
      : size === "lg"
      ? "h-11 min-w-[168px] text-[20px] px-3"
      : "h-8 min-w-[128px] text-[14px] px-2";

  if (unreadable) {
    return (
      <span
        className={`inline-flex items-center justify-center ${dims} ${className} shrink-0 rounded-[3px] border-2 border-black font-data font-semibold tracking-wider text-black/70`}
        style={{
          backgroundImage:
            "repeating-linear-gradient(135deg, #b9c2c9 0px, #b9c2c9 4px, #9aa4ab 4px, #9aa4ab 8px)",
          boxShadow: "0 1px 3px rgba(0,0,0,0.5)",
        }}
        role="img"
        aria-label="Plate unreadable"
      >
        UNREAD
      </span>
    );
  }

  const baseClass = `inline-flex items-center justify-center ${dims} ${className} shrink-0 rounded-[3px] border-2 border-black font-data font-bold tracking-wider text-[var(--plate-ink)]`;
  const style = {
    background: commercial ? "var(--plate-amber)" : "var(--plate-white)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.5)",
  };

  if (!interactive) {
    return (
      <span className={baseClass} style={style} role="img" aria-label={`Plate ${plate}`}>
        {plate}
      </span>
    );
  }

  return (
    <span
      role="button"
      tabIndex={0}
      className={`${baseClass} cursor-pointer hover:brightness-105`}
      style={style}
      aria-label={`Open registry for plate ${plate}`}
      title="View vehicle registry"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        openRegistry(plate);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          e.stopPropagation();
          openRegistry(plate);
        }
      }}
    >
      {plate}
    </span>
  );
}
