"use client";

export function CropThumb({
  cameraLabel,
  offset,
  className = "",
}: {
  cameraLabel: string;
  offset: number;
  className?: string;
}) {
  return (
    <div
      className={`relative overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface-2)] ${className}`}
      style={{
        backgroundImage:
          "repeating-linear-gradient(115deg, rgba(76,195,200,0.05) 0px, rgba(76,195,200,0.05) 2px, transparent 2px, transparent 14px)",
      }}
    >
      <div className="absolute inset-0 flex items-center justify-center">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" className="opacity-25">
          <path
            d="M4 8a2 2 0 012-2h1.2l.9-1.4A2 2 0 019.7 3.6h4.6a2 2 0 011.6 1l.9 1.4H18a2 2 0 012 2v9a2 2 0 01-2 2H6a2 2 0 01-2-2V8z"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <circle cx="12" cy="13" r="3.4" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </div>
      <div className="absolute bottom-1 left-1.5 right-1.5 flex items-center justify-between">
        <span className="font-data text-[9px] text-[var(--muted)]">{cameraLabel}</span>
        <span className="font-data text-[9px] text-[var(--muted)]">t+{offset.toFixed(1)}s</span>
      </div>
      <div className="absolute top-1 right-1.5 h-1.5 w-1.5 rounded-full bg-[var(--danger)]" />
    </div>
  );
}
