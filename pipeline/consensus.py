from collections import Counter
from typing import List, Tuple, Dict


def vote_consensus(reads: List[Dict]) -> Tuple[str, float, str]:
    """Perform multi-frame character-level consensus voting.

    The algorithm:
    * Determine the modal length among non‑empty reads.
    * Keep reads whose length differs from the modal length by at most 1.
    * If at least three reads remain, vote per character weighted by confidence.
      The vote length is the most common length among the kept reads.
    * Otherwise fall back to the single read with highest confidence.

    Returns:
        consensus_text: voted plate string (may be empty).
        consensus_conf: mean confidence of the reads that contributed to the vote.
        method: "character_vote" if ≥3 reads contributed, else "single_frame".
    """
    if not reads:
        return "", 0.0, "single_frame"

    # Count lengths of non‑empty texts
    length_counts = Counter(len(r["text"]) for r in reads if r["text"]) 
    if not length_counts:
        return "", 0.0, "single_frame"

    modal_len = length_counts.most_common(1)[0][0]

    # Keep reads within ±1 of modal length
    filtered = [r for r in reads if abs(len(r["text"]) - modal_len) <= 1]

    if len(filtered) < 3:
        best = max(filtered, key=lambda r: r["conf"], default={"text": "", "conf": 0.0})
        return best["text"], best.get("conf", 0.0), "single_frame"

    # Determine the most common length among filtered reads for alignment
    vote_len_counts = Counter(len(r["text"]) for r in filtered)
    vote_len = vote_len_counts.most_common(1)[0][0]

    aligned = [r for r in filtered if len(r["text"]) == vote_len]

    # Aggregate confidence per character position
    consensus_chars = []
    for i in range(vote_len):
        char_conf: Dict[str, float] = {}
        for r in aligned:
            ch = r["text"][i]
            char_conf[ch] = char_conf.get(ch, 0.0) + r["conf"]
        best_char = max(char_conf.items(), key=lambda item: item[1])[0]
        consensus_chars.append(best_char)

    consensus_text = "".join(consensus_chars)
    mean_conf = sum(r["conf"] for r in aligned) / len(aligned)
    return consensus_text, mean_conf, "character_vote"
