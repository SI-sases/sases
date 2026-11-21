"""UI 快照对比：像素差 + diff 图。"""
import argparse
import os
import sys

try:
    from PIL import Image, ImageChops
except Exception:
    raise SystemExit("需要 Pillow：venv312\\Scripts\\pip install pillow")


def compare(a_path, b_path, out_diff, threshold=0.005):
    a = Image.open(a_path).convert("RGB")
    b = Image.open(b_path).convert("RGB")
    if a.size != b.size:
        return False, 1.0, "size mismatch %s vs %s" % (a.size, b.size)
    diff = ImageChops.difference(a, b)
    bbox = diff.getbbox()
    if not bbox:
        return True, 0.0, "identical"
    hist = diff.convert("L").histogram()
    total = a.size[0] * a.size[1]
    changed = sum(hist[8:])
    ratio = changed / float(total)
    diff.save(out_diff)
    return ratio <= threshold, ratio, bbox


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="tests/ui/baseline")
    ap.add_argument("--current", default="tests/ui/current")
    ap.add_argument("--out", default="tests/ui/diff")
    ap.add_argument("--threshold", type=float, default=0.005)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    names = [n for n in os.listdir(args.baseline) if n.endswith(".png")]
    failed = 0
    for n in names:
        a = os.path.join(args.baseline, n)
        b = os.path.join(args.current, n)
        if not os.path.isfile(b):
            print("MISSING " + n)
            failed += 1
            continue
        ok, ratio, info = compare(a, b, os.path.join(args.out, n.replace(".png", ".diff.png")), args.threshold)
        print(("OK   " if ok else "FAIL ") + n + " ratio=%.4f %s" % (ratio, info))
        if not ok:
            failed += 1
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
