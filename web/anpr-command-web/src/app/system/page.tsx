export default function SystemPage() {
  return (
    <div className="p-4 sm:p-6 max-w-[1100px] mx-auto">
      <div className="mb-6">
        <div className="eyebrow mb-1">System</div>
        <h1 className="font-display text-2xl sm:text-3xl font-semibold">How this actually works</h1>
        <p className="text-sm text-[var(--muted)] mt-1 max-w-2xl">
          This page replaces the deck. Everything here is meant to be read without a presenter in the room.
        </p>
      </div>

      <section className="card p-5 mb-5">
        <div className="eyebrow mb-4">Architecture</div>
        <svg viewBox="0 0 900 300" className="w-full h-auto" role="img" aria-label="Pipeline architecture diagram">
          <defs>
            <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#4CC3C8" />
            </marker>
          </defs>
          {[
            { x: 10, y: 110, w: 120, h: 60, label: "Camera feed", sub: "8 fixed ANPR points" },
            { x: 170, y: 110, w: 140, h: 60, label: "Detection + OCR", sub: "per-frame plate reads" },
            { x: 350, y: 110, w: 150, h: 60, label: "Consensus vote", sub: "character-vote across frames" },
            { x: 540, y: 40, w: 150, h: 60, label: "Watchlist match", sub: "→ alerts" },
            { x: 540, y: 180, w: 150, h: 60, label: "Postgres (Supabase)", sub: "sightings · cases · alerts" },
            { x: 730, y: 110, w: 155, h: 60, label: "Next.js API + UI", sub: "live query, no adapters" },
          ].map((b, i) => (
            <g key={i}>
              <rect x={b.x} y={b.y} width={b.w} height={b.h} rx="8" fill="#1A232B" stroke="#26313B" />
              <text x={b.x + b.w / 2} y={b.y + 26} textAnchor="middle" fill="#E8EEF2" fontSize="13" fontFamily="var(--font-display)" fontWeight={600}>
                {b.label}
              </text>
              <text x={b.x + b.w / 2} y={b.y + 44} textAnchor="middle" fill="#8494A1" fontSize="10" fontFamily="var(--font-body)">
                {b.sub}
              </text>
            </g>
          ))}
          <path d="M130,140 L165,140" stroke="#4CC3C8" strokeWidth="2" markerEnd="url(#arrow)" fill="none" />
          <path d="M310,140 L345,140" stroke="#4CC3C8" strokeWidth="2" markerEnd="url(#arrow)" fill="none" />
          <path d="M500,140 L525,140 L525,70 L535,70" stroke="#4CC3C8" strokeWidth="2" markerEnd="url(#arrow)" fill="none" />
          <path d="M500,140 L525,140 L525,210 L535,210" stroke="#4CC3C8" strokeWidth="2" markerEnd="url(#arrow)" fill="none" />
          <path d="M690,70 L710,70 L710,130 L725,130" stroke="#4CC3C8" strokeWidth="2" markerEnd="url(#arrow)" fill="none" />
          <path d="M690,210 L710,210 L710,150 L725,150" stroke="#4CC3C8" strokeWidth="2" markerEnd="url(#arrow)" fill="none" />
        </svg>
      </section>

      <section className="card p-5 mb-5">
        <div className="eyebrow mb-3">Prototype vs. target architecture</div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[var(--muted)] eyebrow">
              <th className="py-2 pr-4">Layer</th>
              <th className="py-2 pr-4">This build</th>
              <th className="py-2">Target production</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {[
              ["Camera network", "8 fixed points, static lat/lon, simulated geography", "Municipal ANPR network with verified road-distance calibration"],
              ["Detection + OCR", "Fixture-synthetic reads, real consensus pipeline logic", "Real-time YOLO/plate-detector + multi-frame OCR ensemble on live RTSP"],
              ["Database", "Supabase Postgres, seeded from schema-identical fixture", "Same schema, continuously written by the live pipeline"],
              ["Registry cross-reference", "Seeded mock watchlist (3 entries)", "VAHAN / state MVD integration — restricted government API, no public access"],
              ["API + frontend", "Next.js API routes reading Postgres directly, live", "Same contract; horizontally scaled behind the same schema"],
            ].map((row, i) => (
              <tr key={i}>
                <td className="py-2.5 pr-4 font-medium">{row[0]}</td>
                <td className="py-2.5 pr-4 text-[var(--muted)]">{row[1]}</td>
                <td className="py-2.5 text-[var(--muted)]">{row[2]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card p-5 mb-5">
        <div className="eyebrow mb-3">What&apos;s real vs. simulated</div>
        <ul className="text-sm space-y-2 text-[var(--muted)]">
          <li>
            <span className="text-[var(--text)] font-medium">Real: </span>
            the entire data layer — Postgres schema, live queries, trajectory/leg computation, anomaly detection,
            consensus voting, watchlist matching and alert generation all execute against a live database, not
            mock JSON in the frontend bundle.
          </li>
          <li>
            <span className="text-[var(--text)] font-medium">Simulated: </span>
            the camera network geography and the plate reads themselves are seeded fixture data — synthetic,
            not pulled from real footage. The consensus voting shown on <code className="font-data">/review</code>{" "}
            is the same algorithm the pipeline uses, run live on this fixture data.
          </li>
          <li>
            <span className="text-[var(--text)] font-medium">Standing in for a restricted system: </span>
            the watchlist is a seeded mock registry. India&apos;s actual vehicle registry (VAHAN) is a restricted
            government system with no public API — any real deployment integrates there instead.
          </li>
        </ul>
      </section>

      <section className="card p-5 mb-5">
        <div className="eyebrow mb-3">Measured OCR bake-off</div>
        <p className="text-sm text-[var(--muted)]">
          This fixture set has no ground-truth benchmark attached (<code className="font-data">ocr_benchmark_plate_acc: null</code>{" "}
          in the schema) — the OCR model tag is <code className="font-data">fixture-synthetic</code>. Plate-level accuracy
          numbers will be published once the pipeline runs against staged real footage at Checkpoint 2.
        </p>
      </section>

      <section className="card p-5">
        <div className="eyebrow mb-3">Known limitations</div>
        <ul className="text-sm space-y-2 text-[var(--muted)] list-disc pl-4">
          <li>Severely bent or non-planar plates are an open research problem — the pipeline flags these as low-confidence rather than silently misreading them.</li>
          <li>Speed-anomaly detection uses a fixed 150 km/h threshold between consecutive sightings; it will over-flag on cameras that are geographically close but not directly road-linked, which is why unlinked pairs fall back to a haversine-based estimate rather than a hard failure.</li>
          <li>Fuzzy-merge detection surfaces near-miss raw reads per sighting; it does not yet cross-reference against other plates in the fleet to disambiguate genuine clones from OCR noise.</li>
          <li>The watchlist has no expiry or review workflow — entries persist until manually removed.</li>
        </ul>
      </section>
    </div>
  );
}
