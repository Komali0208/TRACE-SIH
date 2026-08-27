"use client";

import { useEffect, useMemo, useState } from "react";
import { PlateChip } from "@/components/PlateChip";
import { voteConsensus } from "@/lib/utils";
import { RawRead } from "@/lib/types";

const FRAME_MS = 190;

function lockedMask(prefix: RawRead[]): boolean[] {
  const texts = prefix.map((r) => r.text || "").filter(Boolean);
  if (texts.length === 0) return [];
  const len = Math.max(...texts.map((t) => t.length));
  const mask: boolean[] = [];
  for (let i = 0; i < len; i++) {
    const counts = new Map<string, number>();
    let n = 0;
    for (const t of texts) {
      const ch = t[i];
      if (!ch || ch === "_") continue;
      n += 1;
      counts.set(ch, (counts.get(ch) || 0) + 1);
    }
    let best = 0;
    for (const v of counts.values()) if (v > best) best = v;
    mask.push(n >= 2 && best >= Math.ceil(n * 0.6));
  }
  return mask;
}

export function ConsensusVote({
  reads,
  consensus,
  frameCount,
  method,
  compact = false,
}: {
  reads: RawRead[];
  consensus: string | null;
  frameCount?: number;
  method?: string;
  compact?: boolean;
}) {
  const usable = reads.filter((r) => r.text);
  const [phase, setPhase] = useState<"idle" | "playing" | "done">("idle");
  const [idx, setIdx] = useState(0);

  const finalPlate = consensus || voteConsensus(usable);

  useEffect(() => {
    if (phase !== "playing" || usable.length === 0) return;
    if (idx >= usable.length) {
      setPhase("done");
      return;
    }
    const t = setTimeout(() => setIdx((i) => i + 1), FRAME_MS);
    return () => clearTimeout(t);
  }, [phase, idx, usable.length]);

  function replay() {
    if (usable.length === 0) return;
    setIdx(0);
    setPhase("playing");
  }

  const prefix = phase === "playing" ? usable.slice(0, idx + 1) : usable;
  const current = usable[Math.min(idx, Math.max(usable.length - 1, 0))];
  const running = voteConsensus(prefix);
  const locks = useMemo(() => lockedMask(prefix), [prefix]);
  const agreed = usable.filter((r) => r.text === finalPlate).length;
  const nFrames = frameCount ?? usable.length;
  const caption = `${nFrames} frames voted, ${agreed} agreed${method ? ` · ${method.replace(/_/g, " ")}` : ""}`;

  if (usable.length === 0) {
    return (
      <div>
        <PlateChip plate={finalPlate || null} size={compact ? "sm" : "md"} />
        <p className="text-[11px] text-[var(--muted)] mt-1">No per-frame reads on this sighting.</p>
      </div>
    );
  }

  const showChars = phase === "playing" && current;
  const display = showChars ? current.text : running;

  return (
    <div className={compact ? "flex flex-col gap-1.5" : "flex flex-col gap-2"}>
      {phase === "idle" && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="opacity-45">
            <PlateChip plate={finalPlate || null} size={compact ? "sm" : "md"} />
          </span>
          <button
            type="button"
            onClick={replay}
            className="eyebrow rounded-md border border-[var(--border)] px-2 py-1 text-[var(--signal)] hover:bg-black/5"
          >
            Show reasoning
          </button>
        </div>
      )}

      {phase === "playing" && (
        <div>
          <div
            className={`inline-flex items-center font-data font-bold tracking-wider rounded-[3px] border-2 border-[var(--signal)]/40 bg-[var(--surface)] px-2 ${
              compact ? "h-6 text-[11px]" : "h-8 text-[14px]"
            }`}
            style={{ animation: "plateJitter 0.18s ease-in-out infinite" }}
            aria-live="polite"
          >
            {display.split("").map((ch, i) => (
              <span
                key={i}
                className="inline-block min-w-[0.65em] text-center"
                style={{
                  color: locks[i] ? "var(--signal)" : "var(--muted)",
                  opacity: locks[i] ? 1 : 0.7,
                }}
              >
                {ch === "_" ? "·" : ch}
              </span>
            ))}
          </div>
          <div className="mt-1 flex items-center gap-2 text-[11px] text-[var(--muted)] font-data">
            <span>
              frame {current?.frame ?? idx + 1} · {Math.round((current?.conf ?? 0) * 100)}%
            </span>
            <span>
              {idx + 1}/{usable.length}
            </span>
          </div>
        </div>
      )}

      {phase === "done" && (
        <div>
          <div className="inline-block origin-left" style={{ animation: "plateSnap 0.28s ease-out both" }}>
            <PlateChip plate={finalPlate || null} size={compact ? "sm" : "md"} />
          </div>
          <p className="text-[11px] text-[var(--muted)] mt-1">{caption}</p>
          <button
            type="button"
            onClick={replay}
            className="eyebrow mt-1 rounded-md border border-[var(--border)] px-2 py-1 text-[var(--signal)] hover:bg-black/5"
          >
            Replay
          </button>
        </div>
      )}
    </div>
  );
}
