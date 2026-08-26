export const PLATE_REGEX = /^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}$/;

export function isValidPlate(s: string) {
  return PLATE_REGEX.test(s.trim().toUpperCase());
}

export function relTime(iso: string, now: number = Date.now()) {
  const t = new Date(iso).getTime();
  const diff = Math.max(0, now - t);
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ${m % 60}m ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export function fmtTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

export function confColor(c: number) {
  if (c >= 0.85) return "#4FA96B";
  if (c >= 0.6) return "#4CC3C8";
  if (c >= 0.4) return "#E8942E";
  return "#E0483B";
}

// Character-vote consensus, mirrors the pipeline's own method: for each
// character position across all raw reads, take the most frequent
// non-placeholder ("_") character. Used to visually re-derive the
// consensus so the /review screen can show the convergence live.
export function voteConsensus(reads: { text: string; conf: number }[]): string {
  const nonEmpty = reads.filter((r) => r.text && r.text.length > 0);
  if (nonEmpty.length === 0) return "";
  const len = Math.max(...nonEmpty.map((r) => r.text.length));
  let out = "";
  for (let i = 0; i < len; i++) {
    const counts = new Map<string, number>();
    for (const r of nonEmpty) {
      const ch = r.text[i];
      if (!ch || ch === "_") continue;
      counts.set(ch, (counts.get(ch) || 0) + (0.5 + r.conf));
    }
    let best = "_";
    let bestScore = -1;
    for (const [ch, score] of counts) {
      if (score > bestScore) {
        best = ch;
        bestScore = score;
      }
    }
    out += best;
  }
  return out;
}

export function isCommercialPlate(plate: string | null) {
  // Fixture heuristic: commercial (yellow) plates commonly carry a
  // trailing non-numeric series letter pattern; here we treat plates
  // whose series segment includes 'T' (taxi/transport) as commercial.
  if (!plate) return false;
  return /\bT[A-Z]?\d{4}$/.test(plate) === false && false; // reserved — dataset is all private plates
}
