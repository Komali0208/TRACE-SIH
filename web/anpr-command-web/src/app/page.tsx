"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useDataMode } from "@/lib/mode";
import { useSnapshot } from "@/lib/useSnapshot";
import { PlateChip } from "@/components/PlateChip";
import { ConfidenceBar, FlagChip, Skeleton } from "@/components/Chips";
import { relTime, fmtTime } from "@/lib/utils";
import { Camera, Sighting } from "@/lib/types";

const MapView = dynamic(() => import("@/components/MapView").then((m) => m.MapView), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

function KpiTile({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="card p-4 flex flex-col gap-1">
      <div className="eyebrow">{label}</div>
      <div
        className="font-display text-[40px] leading-none font-semibold"
        style={{ color: accent ?? "var(--text)" }}
      >
        {value}
      </div>
    </div>
  );
}

function Tour({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0);
  const steps = [
    { title: "Drag the timeline", body: "Scrub through the recording window — the map and event feed filter live to whatever moment you land on." },
    { title: "Search any plate", body: "Trajectory reconstructs sighting → leg → sighting across the whole camera network, with anomaly detection built in." },
    { title: "Review the OCR queue", body: "Every flagged read shows its full multi-frame consensus — how five noisy reads become one clean plate." },
  ];
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="card glass w-full max-w-sm p-5 animate-rise">
        <div className="eyebrow mb-1">Step {step + 1} of 3</div>
        <div className="font-display text-xl font-semibold mb-2">{steps[step].title}</div>
        <p className="text-sm text-[var(--muted)] mb-5">{steps[step].body}</p>
        <div className="flex items-center justify-between">
          <button onClick={onDone} className="text-xs text-[var(--muted)] hover:text-[var(--text)]">
            Skip
          </button>
          <button
            onClick={() => (step < 2 ? setStep(step + 1) : onDone())}
            className="rounded-lg bg-[var(--signal)] text-black text-sm font-semibold px-4 py-2 hover:brightness-110 transition"
          >
            {step < 2 ? "Next" : "Start exploring"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CommandCentre() {
  const { mode } = useDataMode();
  const snap = useSnapshot(mode === "cached");
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [sightings, setSightings] = useState<Sighting[] | null>(null);
  const [summary, setSummary] = useState<any>(null);
  const [cursor, setCursor] = useState<number | null>(null);
  const [windowMin, setWindowMin] = useState(12);
  // Tour disabled by default to keep dashboard clear and interactive
  const [showTour, setShowTour] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (mode === "live") {
      fetch("/api/cameras").then((r) => r.json()).then((d) => setCameras(d.cameras));
      fetch("/api/sightings?limit=500").then((r) => r.json()).then((d) => setSightings(d.sightings));
      fetch("/api/analytics/summary").then((r) => r.json()).then((d) => setSummary(d.summary));
    } else if (mode === "cached" && snap) {
      setCameras(snap.cameras);
      setSightings([...snap.sightings].sort((a, b) => +new Date(b.ts) - +new Date(a.ts)));
      const unique = new Set(snap.sightings.map((s) => s.plate_text).filter(Boolean)).size;
      const mean = snap.sightings.reduce((a, s) => a + s.plate_confidence, 0) / snap.sightings.length;
      setSummary({
        total_sightings: snap.sightings.length,
        unique_plates: unique,
        mean_confidence: mean,
        open_alerts: 5,
        open_review_cases: 15,
      });
    }
  }, [mode, snap]);

  const timeBounds = useMemo(() => {
    if (!sightings || sightings.length === 0) return null;
    const times = sightings.map((s) => +new Date(s.ts));
    return { min: Math.min(...times), max: Math.max(...times) };
  }, [sightings]);

  useEffect(() => {
    if (timeBounds && cursor === null) setCursor(timeBounds.max);
  }, [timeBounds, cursor]);

  useEffect(() => {
    const el = feedRef.current;
    if (!el) return;
    let raf: number;
    let y = 0;
    const step = () => {
      y += 0.3;
      if (y < 60) {
        el.scrollTop = y;
        raf = requestAnimationFrame(step);
      } else {
        setTimeout(() => (el.scrollTop = 0), 900);
      }
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [sightings]);

  const windowed = useMemo(() => {
    if (!sightings || cursor === null) return sightings ?? [];
    const lo = cursor - windowMin * 60000;
    return sightings.filter((s) => {
      const t = +new Date(s.ts);
      return t <= cursor && t >= lo;
    });
  }, [sightings, cursor, windowMin]);

  const activeIds = useMemo(() => new Set(windowed.map((s) => s.camera_id)), [windowed]);
  const cameraName = (id: string) => cameras?.find((c) => c.id === id)?.name ?? id;

  const loading = !cameras || !sightings || !summary || cursor === null;

  return (
    <div className="p-4 sm:p-6 max-w-[1600px] mx-auto">
      {showTour && <Tour onDone={dismissTour} />}

      <div className="mb-5">
        <div className="eyebrow mb-1">Command centre</div>
        <h1 className="font-display text-2xl sm:text-3xl font-semibold">
          Multi-camera vehicle intelligence, live across the Bengaluru grid
        </h1>
        <p className="text-sm text-[var(--muted)] mt-1 max-w-2xl">
          8 ANPR cameras · every plate read, cross-referenced against a watchlist, and reconstructed into
          trajectories in real time.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[92px]" />)
        ) : (
          <>
            <KpiTile label="Vehicles seen" value={String(summary.total_sightings)} />
            <KpiTile label="Unique plates" value={String(summary.unique_plates)} accent="var(--signal)" />
            <KpiTile label="Mean confidence" value={`${Math.round(summary.mean_confidence * 100)}%`} />
            <KpiTile
              label="Open alerts"
              value={String(summary.open_alerts)}
              accent={summary.open_alerts > 0 ? "var(--danger)" : "var(--ok)"}
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-4">
        <div className="card overflow-hidden flex flex-col h-[480px] xl:h-[620px]">
          <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
            <div className="eyebrow">Live event feed</div>
            <Link href="/trajectory" className="text-[11px] text-[var(--signal)] hover:underline">
              Search a plate →
            </Link>
          </div>
          <div ref={feedRef} className="flex-1 overflow-y-auto divide-y divide-[var(--border)]">
            {loading
              ? Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-16 m-2" />)
              : windowed.slice(0, 60).map((s) => (
                  <Link
                    key={s.id}
                    href={s.plate_text ? `/trajectory?plate=${s.plate_text}` : "/review"}
                    className="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors"
                  >
                    <PlateChip plate={s.plate_text} size="sm" />
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-medium truncate">{cameraName(s.camera_id)}</div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <ConfidenceBar value={s.plate_confidence} width={44} />
                        {s.flags[0] && <FlagChip flag={s.flags[0]} />}
                      </div>
                    </div>
                    <div className="text-[10px] font-data text-[var(--muted)] shrink-0">{relTime(s.ts, cursor ?? Date.now())}</div>
                  </Link>
                ))}
            {!loading && windowed.length === 0 && (
              <div className="p-6 text-center text-xs text-[var(--muted)]">No sightings in this time window.</div>
            )}
          </div>
        </div>

        <div className="card overflow-hidden h-[480px] xl:h-[620px] relative">
          {loading ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <MapView cameras={cameras!} activeIds={activeIds} />
          )}
          <div className="absolute top-3 left-3 z-[400] glass rounded-lg px-3 py-2 text-[11px] flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--signal)] animate-pulseMarker" />
            {activeIds.size} camera{activeIds.size === 1 ? "" : "s"} active in window
          </div>
        </div>
      </div>

      {!loading && timeBounds && (
        <div className="card mt-4 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="eyebrow">Timeline scrubber</div>
            <div className="font-data text-xs text-[var(--muted)]">
              {fmtTime(new Date(cursor! - windowMin * 60000).toISOString())} — {fmtTime(new Date(cursor!).toISOString())}{" "}
              <span className="text-[var(--signal)] ml-2">{windowMin}m window</span>
            </div>
          </div>
          <input
            type="range"
            min={timeBounds.min}
            max={timeBounds.max}
            value={cursor ?? timeBounds.max}
            onChange={(e) => setCursor(Number(e.target.value))}
            className="w-full accent-[var(--signal)] h-2 cursor-pointer"
            aria-label="Timeline scrubber"
          />
          <div className="flex justify-between text-[10px] font-data text-[var(--muted)] mt-1">
            <span>{fmtTime(new Date(timeBounds.min).toISOString())}</span>
            <span>{fmtTime(new Date(timeBounds.max).toISOString())}</span>
          </div>
        </div>
      )}
    </div>
  );
}
