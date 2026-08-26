"""
spike/00_env.py — Environment sanity check.
Run this FIRST. If the GPU isn't visible here, nothing downstream will use it.

Usage: python spike/00_env.py
"""
import sys, importlib, platform

print("=" * 60)
print("SPIKE ENVIRONMENT CHECK")
print("=" * 60)

# ── Python ───────────────────────────────────────────────────
print(f"\nPython:  {sys.version}")
print(f"OS:      {platform.system()} {platform.release()}")

# ── CUDA via torch (optional) ────────────────────────────────
try:
    import torch
    print(f"\nPyTorch: {torch.__version__}")
    print(f"CUDA available (torch): {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device: {torch.cuda.get_device_name(0)}")
        print(f"CUDA version: {torch.version.cuda}")
    else:
        print("⚠  torch sees NO CUDA — models will run on CPU")
except ImportError:
    print("\nPyTorch: not installed (EasyOCR needs it — expect that to fail)")

# ── ONNX Runtime ─────────────────────────────────────────────
try:
    import onnxruntime as ort
    print(f"\nonnxruntime: {ort.__version__}")
    providers = ort.get_available_providers()
    print(f"Execution providers: {providers}")
    if "CUDAExecutionProvider" in providers:
        print("✓  CUDA EP available — ONNX models will use GPU")
    elif "TensorrtExecutionProvider" in providers:
        print("✓  TensorRT EP available — ONNX models will use GPU")
    else:
        print("⚠  No GPU execution provider — ONNX models will use CPU only")
except ImportError:
    print("\nonnxruntime: NOT INSTALLED")

# ── Package versions ─────────────────────────────────────────
packages = [
    "fast_alpr",
    "fast_plate_ocr",
    "paddleocr",
    "paddle",       # paddlepaddle imports as paddle
    "easyocr",
    "cv2",          # opencv-python
    "supervision",
    "ultralytics",
    "numpy",
    "Levenshtein",
]

print("\n── Package versions ──")
for pkg in packages:
    try:
        mod = importlib.import_module(pkg)
        ver = getattr(mod, "__version__", "installed (no __version__)")
        print(f"  {pkg:20s} {ver}")
    except ImportError:
        print(f"  {pkg:20s} ✗ NOT FOUND")
    except Exception as e:
        print(f"  {pkg:20s} ✗ import error: {e}")

# ── Summary verdict ──────────────────────────────────────────
print("\n" + "=" * 60)
gpu_ok = False
try:
    import torch
    if torch.cuda.is_available():
        gpu_ok = True
except ImportError:
    pass
try:
    import onnxruntime as ort
    if "CUDAExecutionProvider" in ort.get_available_providers():
        gpu_ok = True
except ImportError:
    pass

if gpu_ok:
    print("✓  GPU IS AVAILABLE — models should use it")
else:
    print("⚠  NO GPU DETECTED — everything will run on CPU (slower, but works)")
print("=" * 60)
