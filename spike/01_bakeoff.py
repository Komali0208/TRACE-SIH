"""
spike/01_bakeoff.py — Benchmark 3 OCR engines on cropped Indian plates.
Reads from spike/bakeoff/crops/*.jpg and spike/bakeoff/ground_truth.csv

Usage: python spike/01_bakeoff.py

Outputs:
  - spike/BAKEOFF.md   (markdown table)
  - stdout             (same table + winner banner)
"""
import os, sys, time, re, csv
from pathlib import Path

SPIKE = Path(__file__).resolve().parent
CROPS = SPIKE / "bakeoff" / "crops"
GT_CSV = SPIKE / "bakeoff" / "ground_truth.csv"
OUT_MD = SPIKE / "BAKEOFF.md"

# ── Validate inputs ──────────────────────────────────────────
if not CROPS.exists() or not any(CROPS.glob("*.jpg")):
    print(f"ERROR: No crop images found at {CROPS}")
    print("Put ~60 cropped Indian licence-plate JPGs in spike/bakeoff/crops/")
    sys.exit(1)

if not GT_CSV.exists():
    print(f"ERROR: Ground truth CSV not found at {GT_CSV}")
    print("Create spike/bakeoff/ground_truth.csv with columns: filename, plate_text")
    print("plate_text should be UPPERCASE, no spaces (e.g. KA05MH1234)")
    sys.exit(1)

# ── Load ground truth ────────────────────────────────────────
def normalise(text: str) -> str:
    """Uppercase, strip spaces/hyphens/dots, keep only A-Z 0-9."""
    return re.sub(r"[^A-Z0-9]", "", text.upper())

gt = {}
with open(GT_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        fn = row["filename"].strip()
        gt[fn] = normalise(row["plate_text"])

crop_files = sorted(CROPS.glob("*.jpg"))
# only benchmark crops that have ground truth
crop_files = [c for c in crop_files if c.name in gt]
if not crop_files:
    print("ERROR: No crop filenames match the ground_truth.csv entries.")
    print(f"  CSV has: {list(gt.keys())[:5]} ...")
    print(f"  Folder has: {[c.name for c in sorted(CROPS.glob('*.jpg'))[:5]]} ...")
    sys.exit(1)

print(f"Loaded {len(crop_files)} crops with ground truth.\n")

# ── Metrics ──────────────────────────────────────────────────
def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance."""
    try:
        import Levenshtein
        return Levenshtein.distance(a, b)
    except ImportError:
        # fallback: dynamic programming
        if len(a) < len(b):
            return edit_distance(b, a)
        if len(b) == 0:
            return len(a)
        prev = range(len(b) + 1)
        for i, ca in enumerate(a):
            curr = [i + 1]
            for j, cb in enumerate(b):
                curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + (ca != cb)))
            prev = curr
        return prev[len(b)]


def char_accuracy(pred: str, truth: str) -> float:
    """1 - normalised_edit_distance. 1.0 = perfect."""
    if not truth:
        return 1.0 if not pred else 0.0
    return max(0.0, 1.0 - edit_distance(pred, truth) / len(truth))


# ── Engine wrappers ──────────────────────────────────────────
import cv2

results = {}  # engine_name -> {"exact": int, "char_acc": float, "ms": float, "n": int}

# --- 1. fast-plate-ocr ---
try:
    from fast_plate_ocr import ONNXPlateRecognizer
    print("── fast-plate-ocr ──")
    ocr = ONNXPlateRecognizer("cct-s-v2-global-model")

    exact = 0
    char_acc_sum = 0.0
    total_ms = 0.0
    for crop_path in crop_files:
        img = cv2.imread(str(crop_path))
        if img is None:
            continue
        t0 = time.perf_counter()
        preds = ocr.run(img)
        t1 = time.perf_counter()
        total_ms += (t1 - t0) * 1000

        pred_text = normalise(preds[0] if preds else "")
        truth = gt[crop_path.name]
        if pred_text == truth:
            exact += 1
        char_acc_sum += char_accuracy(pred_text, truth)

    n = len(crop_files)
    results["fast-plate-ocr"] = {
        "exact": exact, "char_acc": char_acc_sum / n,
        "ms": total_ms / n, "n": n
    }
    print(f"  Exact match: {exact}/{n} = {exact/n:.1%}")
    print(f"  Char accuracy: {char_acc_sum/n:.3f}")
    print(f"  Mean ms/plate: {total_ms/n:.1f}")
except ImportError:
    print("── fast-plate-ocr: NOT INSTALLED, skipping ──")
    results["fast-plate-ocr"] = None
except Exception as e:
    print(f"── fast-plate-ocr CRASHED: {e} ──")
    results["fast-plate-ocr"] = None

# --- 2. PaddleOCR ---
try:
    from paddleocr import PaddleOCR
    print("\n── PaddleOCR ──")
    paddle = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    exact = 0
    char_acc_sum = 0.0
    total_ms = 0.0
    for crop_path in crop_files:
        img_path = str(crop_path)
        t0 = time.perf_counter()
        result = paddle.ocr(img_path, cls=True)
        t1 = time.perf_counter()
        total_ms += (t1 - t0) * 1000

        # PaddleOCR returns list of lists; concat all detected text
        pred_text = ""
        if result and result[0]:
            for line in result[0]:
                pred_text += line[1][0]
        pred_text = normalise(pred_text)
        truth = gt[crop_path.name]
        if pred_text == truth:
            exact += 1
        char_acc_sum += char_accuracy(pred_text, truth)

    n = len(crop_files)
    results["PaddleOCR"] = {
        "exact": exact, "char_acc": char_acc_sum / n,
        "ms": total_ms / n, "n": n
    }
    print(f"  Exact match: {exact}/{n} = {exact/n:.1%}")
    print(f"  Char accuracy: {char_acc_sum/n:.3f}")
    print(f"  Mean ms/plate: {total_ms/n:.1f}")
except ImportError:
    print("\n── PaddleOCR: NOT INSTALLED, skipping ──")
    results["PaddleOCR"] = None
except Exception as e:
    print(f"\n── PaddleOCR CRASHED: {e} ──")
    results["PaddleOCR"] = None

# --- 3. EasyOCR ---
try:
    import easyocr
    print("\n── EasyOCR ──")
    reader = easyocr.Reader(["en"], gpu=True, verbose=False)
    allowlist = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    exact = 0
    char_acc_sum = 0.0
    total_ms = 0.0
    for crop_path in crop_files:
        img = cv2.imread(str(crop_path))
        if img is None:
            continue
        t0 = time.perf_counter()
        detections = reader.readtext(img, allowlist=allowlist)
        t1 = time.perf_counter()
        total_ms += (t1 - t0) * 1000

        pred_text = normalise("".join(d[1] for d in detections))
        truth = gt[crop_path.name]
        if pred_text == truth:
            exact += 1
        char_acc_sum += char_accuracy(pred_text, truth)

    n = len(crop_files)
    results["EasyOCR"] = {
        "exact": exact, "char_acc": char_acc_sum / n,
        "ms": total_ms / n, "n": n
    }
    print(f"  Exact match: {exact}/{n} = {exact/n:.1%}")
    print(f"  Char accuracy: {char_acc_sum/n:.3f}")
    print(f"  Mean ms/plate: {total_ms/n:.1f}")
except ImportError:
    print("\n── EasyOCR: NOT INSTALLED, skipping ──")
    results["EasyOCR"] = None
except Exception as e:
    print(f"\n── EasyOCR CRASHED: {e} ──")
    results["EasyOCR"] = None

# ── Results table ────────────────────────────────────────────
print("\n" + "=" * 70)
header = "| Engine | Exact Match | Char Accuracy | ms/plate | Status |"
sep    = "|--------|-------------|---------------|----------|--------|"
rows = []
for name in ["fast-plate-ocr", "PaddleOCR", "EasyOCR"]:
    r = results[name]
    if r is None:
        rows.append(f"| {name} | — | — | — | UNAVAILABLE |")
    else:
        rows.append(
            f"| {name} | {r['exact']}/{r['n']} ({r['exact']/r['n']:.1%}) "
            f"| {r['char_acc']:.3f} | {r['ms']:.1f} | OK |"
        )

table = "\n".join([header, sep] + rows)
print(table)

# ── Write BAKEOFF.md ─────────────────────────────────────────
md = f"# OCR Bakeoff Results\n\n{table}\n"

# ── Winner ───────────────────────────────────────────────────
available = {k: v for k, v in results.items() if v is not None}
if available:
    winner = max(available, key=lambda k: (available[k]["exact"] / available[k]["n"], available[k]["char_acc"]))
    w = available[winner]
    score = w["exact"] / w["n"]

    banner = f"""
{'#' * 60}
#
#   WINNER:  {winner}
#   Exact-match accuracy:  {w['exact']}/{w['n']} = {score:.1%}
#   Character accuracy:    {w['char_acc']:.3f}
#   Speed:                 {w['ms']:.1f} ms/plate
#
{'#' * 60}
"""
    print(banner)
    md += f"\n## Winner\n\n**{winner}** — exact-match {score:.1%}, char-accuracy {w['char_acc']:.3f}, {w['ms']:.1f} ms/plate\n"

    if score < 0.5:
        md += "\n> ⚠ **WARNING**: Exact-match accuracy below 50%. Indian plates may need fine-tuning or a different model.\n"
        print("⚠  WARNING: Accuracy below 50% — consider this a RED FLAG for the approach.")
    elif score < 0.7:
        md += "\n> ⚠ Moderate accuracy. Consensus voting may compensate, but investigate further.\n"
else:
    print("\n⚠  ALL ENGINES FAILED — cannot determine a winner.")
    md += "\n## No winner — all engines unavailable or crashed.\n"

with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write(md)
print(f"\nResults written to {OUT_MD}")
