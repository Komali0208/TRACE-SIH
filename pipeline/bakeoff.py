# pipeline/bakeoff.py
"""Bake‑off benchmark for OCR engines.

This script evaluates three OCR back‑ends on the cropped Indian license‑plate
images supplied for the project and writes a markdown summary with the
plate‑level exact‑match accuracy for each engine.

The required inputs are:
- ``ground_truth.csv`` – a CSV file with two columns: ``image_path`` (relative
  to the repo root) and ``plate_text`` (the ground‑truth plate string).
- The folder containing the cropped plate images referenced in the CSV.

The script is safe to run even if one or more OCR libraries are missing – the
corresponding accuracy entry will be reported as ``N/A``.
"""

import csv
import os
import sys
from pathlib import Path
from typing import Callable, List, Tuple

# ---------------------------------------------------------------------------
# Helper: load ground‑truth mapping
# ---------------------------------------------------------------------------
def load_ground_truth(csv_path: Path) -> List[Tuple[Path, str]]:
    """Return a list of ``(image_path, plate_text)`` tuples.

    ``csv_path`` is expected to have a header and two columns: ``image_path``
    and ``plate_text``. The ``image_path`` is interpreted relative to the CSV
    location.
    """
    entries: List[Tuple[Path, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_rel = row.get("image_path") or row.get("image")
            plate = row.get("plate_text") or row.get("plate")
            if not img_rel or not plate:
                continue
            img_path = (csv_path.parent / img_rel).resolve()
            entries.append((img_path, plate.strip().upper()))
    return entries

# ---------------------------------------------------------------------------
# OCR wrappers – each returns a callable ``recognize(image_path) -> str``
# ---------------------------------------------------------------------------
def get_fast_plate_ocr() -> Callable[[Path], str] | None:
    try:
        from fast_plate_ocr import FastPlateOCR
    except ImportError:
        return None
    engine = FastPlateOCR()
    def recognize(img_path: Path) -> str:
        try:
            text, _ = engine.recognize(str(img_path))
        except Exception:
            text = ""
        return text.strip().upper()
    return recognize


def get_paddle_ocr() -> Callable[[Path], str] | None:
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return None
    ocr = PaddleOCR(lang="en", use_angle_cls=False, show_log=False)
    def recognize(img_path: Path) -> str:
        try:
            # PaddleOCR returns a list of results; each result is [box, text, prob]
            result = ocr.ocr(str(img_path), cls=False)
            if result:
                # concatenate all detected strings (usually one plate per image)
                text = "".join(line[1][0] for line in result[0])
            else:
                text = ""
        except Exception:
            text = ""
        return text.strip().upper()
    return recognize


def get_easy_ocr() -> Callable[[Path], str] | None:
    try:
        import easyocr
    except ImportError:
        return None
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    def recognize(img_path: Path) -> str:
        try:
            result = reader.readtext(str(img_path), detail=0)
            text = "".join(result)
        except Exception:
            text = ""
        return text.strip().upper()
    return recognize

# ---------------------------------------------------------------------------
# Accuracy computation
# ---------------------------------------------------------------------------
def compute_accuracy(entries: List[Tuple[Path, str]], recognizer: Callable[[Path], str]) -> float:
    if not entries:
        return 0.0
    matches = 0
    for img_path, gt in entries:
        pred = recognizer(img_path)
        if pred == gt:
            matches += 1
    return matches / len(entries)

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main():
    # Locate the CSV – default location is ``data/ground_truth.csv`` relative to
    # the repository root. Users can override via environment variable.
    repo_root = Path(__file__).resolve().parents[1]  # pipeline/ -> repo root
    csv_path = Path(os.getenv("GROUND_TRUTH_CSV", repo_root / "data" / "ground_truth.csv"))
    if not csv_path.is_file():
        print(f"[ERROR] ground truth CSV not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    entries = load_ground_truth(csv_path)
    if not entries:
        print("[WARN] No entries loaded from ground truth CSV.")
        sys.exit(0)

    # Prepare recognizers
    recognizers = {
        "FastPlateOCR": get_fast_plate_ocr(),
        "PaddleOCR": get_paddle_ocr(),
        "EasyOCR": get_easy_ocr(),
    }

    results: dict[str, str] = {}
    for name, recognizer in recognizers.items():
        if recognizer is None:
            results[name] = "N/A (library not installed)"
            continue
        acc = compute_accuracy(entries, recognizer)
        results[name] = f"{acc * 100:.2f}%"
        print(f"{name} accuracy: {results[name]}")

    # Write markdown report
    out_md = repo_root / "pipeline" / "BAKEOFF.md"
    with out_md.open("w", encoding="utf-8") as f:
        f.write("# OCR Bake‑off Results\n\n")
        f.write("| OCR Engine | Plate‑level Exact‑Match Accuracy |\n")
        f.write("|------------|----------------------------------|\n")
        for name, val in results.items():
            f.write(f"| {name} | {val} |\n")
    print(f"Bake‑off report written to {out_md}")

if __name__ == "__main__":
    main()
