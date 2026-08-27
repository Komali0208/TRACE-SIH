"use client";
import { useEffect, useMemo, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { useDataMode } from "@/lib/mode";
import { useSnapshot } from "@/lib/useSnapshot";
import { PlateChip } from "@/components/PlateChip";
import { CropThumb } from "@/components/CropThumb";
import { ClipPlayer } from "@/components/ClipPlayer";
import { ConsensusVote } from "@/components/ConsensusVote";
import { ConfidenceBar, FlagChip, Skeleton } from "@/components/Chips";
import { fmtTime } from "@/lib/utils";
import { buildLegs, fuzzyMergedFrom } from "@/lib/analytics";
import { Camera, CameraLink, Sighting, TrajectoryLeg } from "@/lib/types";

const MapView = dynamic(() => import("@/components/MapView").then((m) => m.MapView), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

function TrajectoryInner() {
  const { mode } = useDataMode();
  const snap = useSnapshot(mode === "cached");
  const router = useRouter();
  const params = useSearchParams();

  const [query, setQuery] = useState(params.get("plate") ?? "");
  const [suggestions, setSuggestions] = useState<{ plate_text: string; sighting_count: number }[]>([]);
  const [heroPlates, setHeroPlates] = useState<string[]>([]);
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [links, setLinks] = useState<CameraLink[] | null>(null);

  const [result, setResult] = useState<{
    plate_text: string;
    sightings: Sighting[];
    legs: TrajectoryLeg[];
    fuzzy_merged_from: string[];
    watchlist_status: string | null;
  } | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedSightingId, setSelectedSightingId] = useState<string | null>(null);
  const [readability, setReadability] = useState(100);

  useEffect(() => {
    if (mode === "live") {
      fetch("/api/cameras").then((r) => r.json()).then((d) => {
        setCameras(d.cameras);
        setLinks(d.camera_links);
      });
      fetch("/api/snapshot").then((r) => r.json()).then((d) => setHeroPlates(d.meta?.hero_plates ?? []));
    } else if (mode === "cached" && snap) {
      setCameras(snap.cameras);
      setLinks(snap.camera_links);
      setHeroPlates(snap.meta.hero_plates);
    }
  }, [mode, snap]);

  async function runSearch(plate: string) {
    if (!plate) return;
    const p = plate.trim().toUpperCase();
    setQuery(p);
    setLoading(true);
    setNotFound(false);
    setResult(null);
    setSelectedSightingId(null);
    router.replace(`/trajectory?plate=${p}`, { scroll: false });

    if (mode === "live") {
      const res = await fetch(`/api/trajectory/${p}`);
      if (res.status === 404) {
        setNotFound(true);
        setLoading(false);
        return;
      }
      const data = await res.json();
      setResult(data);
      setLoading(false);
    } else if (snap) {
      const own = snap.sightings.filter((s) => s.plate_text === p);
      if (own.length === 0) {
        setNotFound(true);
        setLoading(false);
        return;
      }
      const legs = buildLegs(own, snap.camera_links, snap.cameras);
      const merged = fuzzyMergedFrom(own, p);
      setResult({ plate_text: p, sightings: own.sort((a, b) => +new Date(a.ts) - +new Date(b.ts)), legs, fuzzy_merged_from: merged, watchlist_status: null });
      setLoading(false);
    }
  }

  useEffect(() => {
    const initial = params.get("plate");
    if (initial) runSearch(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }
    const t = setTimeout(async () => {
      if (mode === "live") {
        const res = await fetch(`/api/plates/search?q=${encodeURIComponent(query)}`);
        const d = await res.json();
        setSuggestions(d.matches ?? []);
      } else if (snap) {
        const q = query.toUpperCase();
        const byPlate = new Map<string, number>();
        for (const s of snap.sightings) {
          if (s.plate_text?.includes(q)) byPlate.set(s.plate_text, (byPlate.get(s.plate_text) || 0) + 1);
        }
        setSuggestions(
          Array.from(byPlate.entries()).map(([plate_text, sighting_count]) => ({ plate_text, sighting_count })).slice(0, 8)
        );
      }
    }, 180);
    return () => clearTimeout(t);
  }, [query, mode, snap]);

  const cameraName = (id: string) => cameras?.find((c) => c.id === id)?.name ?? id;
  const routePoints = useMemo(() => {
    if (!result || !cameras) return [];
    return result.sightings.map((s) => {
      const c = cameras.find((cc) => cc.id === s.camera_id);
      return { lat: c?.lat ?? 0, lon: c?.lon ?? 0 };
    });
  }, [result, cameras]);

  const selectedSighting = selectedSightingId
    ? result?.sightings.find((s) => s.id === selectedSightingId) ?? null
    : null;
  const selectedClipUrl = selectedSighting
    ? cameras?.find((c) => c.id === selectedSighting.camera_id)?.clip_url
    : undefined;

  return (
    <div className="p-4 sm:p-6 max-w-[1600px] mx-auto">
      <div className="mb-5">
        <div className="eyebrow mb-1">Trajectory reconstruction</div>
        <h1 className="font-display text-2xl sm:text-3xl font-semibold">Follow a plate across the grid</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          Every sighting, ordered chronologically, with distance, elapsed time and implied speed computed between
          consecutive cameras. Anomalous legs are flagged automatically.
        </p>
      </div>

      <div className="card p-4 mb-4 relative">
        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && runSearch(query)}
            placeholder="SEARCH PLATE — E.G. KA05MH1234"
            className="flex-1 font-data uppercase tracking-wider bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[var(--signal)]"
            aria-label="Search plate"
          />
          <button
            onClick={() => runSearch(query)}
            className="rounded-lg bg-[var(--signal)] text-[#FBF8F1] text-sm font-semibold px-5 hover:brightness-110 transition"
          >
            Trace
          </button>
        </div>
        {suggestions.length > 0 && (
          <div className="absolute left-4 right-4 top-[52px] z-20 card p-1.5 shadow-panel">
            {suggestions.map((s) => (
              <button
                key={s.plate_text}
                onClick={() => {
                  setSuggestions([]);
                  runSearch(s.plate_text);
                }}
                className="w-full flex items-center justify-between px-2.5 py-2 rounded-md hover:bg-black/5 text-left"
              >
                <PlateChip plate={s.plate_text} size="sm" />
                <span className="text-[11px] text-[var(--muted)]">{s.sighting_count} sightings</span>
              </button>
            ))}
          </div>
        )}
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          <span className="eyebrow">Try</span>
          {heroPlates.map((p) => (
            <button key={p} onClick={() => runSearch(p)}>
              <PlateChip plate={p} size="sm" className="hover:brightness-110 transition" />
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_420px] gap-4">
          <Skeleton className="h-[420px]" />
          <Skeleton className="h-[420px]" />
        </div>
      )}

      {notFound && !loading && (
        <div className="card p-8 text-center">
          <div className="font-display text-lg mb-1">No sightings for {query}</div>
          <p className="text-sm text-[var(--muted)]">This plate hasn't been read by any camera in the current dataset.</p>
        </div>
      )}

      {result && !loading && (
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_440px] gap-4">
          <div className="flex flex-col gap-3">
            <div className="card overflow-hidden h-[420px] xl:h-[520px] relative">
              {cameras && (
                <MapView
                  cameras={cameras}
                  routePoints={routePoints}
                  activeIds={new Set(result.sightings.map((s) => s.camera_id))}
                />
              )}
              <div className="absolute top-3 left-3 z-[400] glass rounded-lg px-3 py-2 flex items-center gap-2">
                <PlateChip plate={result.plate_text} size="sm" />
                {result.watchlist_status && (
                  <span className="eyebrow text-[var(--danger)]">{result.watchlist_status}</span>
                )}
              </div>
            </div>

            {selectedSighting && (
              <ClipPlayer
                src={selectedClipUrl}
                offsetS={selectedSighting.video_offset_s}
                label={`${cameraName(selectedSighting.camera_id)} · t+${selectedSighting.video_offset_s.toFixed(1)}s`}
                onClose={() => setSelectedSightingId(null)}
              />
            )}
          </div>

          <div className="flex flex-col gap-3 max-h-[640px] overflow-y-auto pr-1">
            <div className="card p-3">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="eyebrow">Simulate OCR confidence</span>
                <span className="font-data text-[11px] text-[var(--muted)]">{readability}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={readability}
                onChange={(e) => setReadability(Number(e.target.value))}
                className="w-full accent-[var(--signal)] h-2 cursor-pointer"
                aria-label="Plate readability"
              />
              {readability < 40 && (
                <p className="text-[11px] text-[var(--muted)] mt-2">
                  Plate text is unreadable. Trajectory still holds via camera sequence and travel-time plausibility — not a clean OCR string.
                </p>
              )}
            </div>
            {result.fuzzy_merged_from.length > 0 && (
              <div className="card p-3 border-[var(--warn)]/40" style={{ borderColor: "rgba(196,132,42,0.4)" }}>
                <div className="eyebrow text-[var(--warn)] mb-1">Fuzzy merge</div>
                <p className="text-xs text-[var(--muted)]">
                  Noisy raw reads stitched into this plate&apos;s history:{" "}
                  {result.fuzzy_merged_from.map((v) => (
                    <span key={v} className="font-data text-[var(--text)] mr-1.5">
                      {v}
                    </span>
                  ))}
                </p>
              </div>
            )}
            {result.sightings.map((s, i) => (
              <div key={s.id}>
                <button
                  type="button"
                  onClick={() => setSelectedSightingId(s.id)}
                  className={`card p-3 flex gap-3 animate-rise w-full text-left transition-colors cursor-pointer ${
                    selectedSightingId === s.id
                      ? "border-[var(--signal)] ring-1 ring-[var(--signal)]/40"
                      : "hover:bg-black/5"
                  }`}
                >
                  <CropThumb cameraLabel={s.camera_id} offset={s.video_offset_s} className="h-16 w-20 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <PlateChip plate={readability < 40 ? null : s.plate_text} size="sm" />
                      {s.flags.map((f) => (
                        <FlagChip key={f} flag={f} />
                      ))}
                    </div>
                    <div className="text-xs font-medium truncate">{cameraName(s.camera_id)}</div>
                    <div className="flex items-center justify-between mt-1">
                      <span className="font-data text-[10px] text-[var(--muted)]">{fmtTime(s.ts)}</span>
                      <ConfidenceBar value={Math.min(s.plate_confidence, readability / 100)} width={50} />
                    </div>
                  </div>
                </button>
                {selectedSightingId === s.id && s.raw_reads?.length > 0 && readability >= 40 && (
                  <div className="card p-3 mt-1.5">
                    <ConsensusVote
                      reads={s.raw_reads}
                      consensus={s.plate_text}
                      frameCount={s.frame_count}
                      method={s.consensus_method}
                      compact
                    />
                  </div>
                )}
                {result.legs[i] && <LegRow leg={result.legs[i]} />}
              </div>
            ))}
          </div>
        </div>
      )}

      {!result && !loading && !notFound && (
        <div className="card p-10 text-center">
          <div className="font-display text-lg mb-1">Search a plate to reconstruct its journey</div>
          <p className="text-sm text-[var(--muted)]">Try one of the example plates above — each has 3+ sightings across the grid.</p>
        </div>
      )}
    </div>
  );
}

function LegRow({ leg }: { leg: TrajectoryLeg }) {
  const danger = leg.anomaly;
  return (
    <div
      className="flex items-center gap-2 my-1.5 pl-4 border-l-2 ml-8"
      style={{ borderColor: danger ? "var(--danger)" : "var(--border)" }}
    >
      <div className={`text-[11px] font-data flex items-center gap-2 py-1 ${danger ? "text-[var(--danger)]" : "text-[var(--muted)]"}`}>
        <span>↓</span>
        <span>
          {(leg.road_distance_m / 1000).toFixed(1)} km · {leg.elapsed_seconds}s · {leg.implied_speed_kmh} km/h implied
        </span>
        {danger && (
          <span className="eyebrow rounded px-1.5 py-0.5 border border-[var(--danger)]/50 bg-[var(--danger)]/15 text-[var(--danger)]">
            Clone suspected
          </span>
        )}
      </div>
      {danger && leg.anomaly_reason && (
        <div className="sr-only">{leg.anomaly_reason}</div>
      )}
      {danger && (
        <p className="text-[11px] text-[var(--danger)]/90 ml-2">{leg.anomaly_reason}</p>
      )}
    </div>
  );
}

export default function TrajectoryPage() {
  return (
    <Suspense fallback={<div className="p-6"><Skeleton className="h-96" /></div>}>
      <TrajectoryInner />
    </Suspense>
  );
}
