import torch
import numpy as np
import os
import re

# --- CONFIG ---
INPUT_DIR = "./input_yuv/class_B"
OUTPUT_ROOT = "./output"
ROI_DIR = "./roi/yolov5"
REPORT_FILE = "psnr_3_7_results.txt"
TARGET_QPS = [22, 27, 32, 37, 42, 47]

# --------------------------------------------------
def parse_res(name):
    m = re.search(r'(\d+)x(\d+)', name)
    return (int(m.group(1)), int(m.group(2))) if m else (1920, 1080)

# --------------------------------------------------
def load_roi_mask(roi_file, h, w):
    mask = np.zeros((h, w), dtype=np.bool_)

    if not os.path.exists(roi_file):
        return mask

    with open(roi_file, "r") as f:
        for line in f:
            x1, y1, x2, y2 = map(int, line.strip().split(","))
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)
            mask[y1:y2, x1:x2] = True

    return mask

# --------------------------------------------------
def psnr_masked(a, b, mask):
    diff = (a - b) ** 2
    diff = diff[mask]

    if diff.numel() == 0:
        return float("nan")

    mse = diff.mean()
    if mse == 0:
        return 100.0

    return (20 * torch.log10(255.0 / torch.sqrt(mse))).item()

# --------------------------------------------------
def read_y_only(path, w, h):
    frame_size = w * h * 3 // 2
    y_size = w * h

    raw = np.fromfile(path, dtype=np.uint8)
    n_frames = raw.size // frame_size
    raw = raw.reshape(n_frames, frame_size)

    Y = raw[:, :y_size].reshape(n_frames, h, w)
    return torch.from_numpy(Y).float(), n_frames

# --------------------------------------------------
def main():
    methods = sorted(
        d for d in os.listdir(OUTPUT_ROOT)
        if os.path.isdir(os.path.join(OUTPUT_ROOT, d))
    )

    summary = {m: {qp: [] for qp in TARGET_QPS} for m in methods}

    with open(REPORT_FILE, "w") as f:
        header = (
            f"{'Method':<10} | {'Sequence':<25} | {'QP':<4} | "
            f"{'ROI-Y':<8} | {'nonROI-Y':<10} | {'AVG(0.7/0.3)':<12}"
        )
        print(header)
        f.write(header + "\n")
        f.write("-" * 90 + "\n")

        for method in methods:
            for qp in TARGET_QPS:
                qp_dir = os.path.join(OUTPUT_ROOT, method, f"qp{qp}")
                if not os.path.exists(qp_dir):
                    continue

                for fname in sorted(x for x in os.listdir(qp_dir) if x.endswith(".yuv")):
                    w, h = parse_res(fname)

                    oy, n1 = read_y_only(os.path.join(INPUT_DIR, fname), w, h)
                    dy, n2 = read_y_only(os.path.join(qp_dir, fname), w, h)
                    n = min(n1, n2)

                    roi_root = os.path.join(ROI_DIR, os.path.splitext(fname)[0])

                    roi_vals, nonroi_vals = [], []

                    for i in range(n):
                        roi_file = os.path.join(roi_root, f"frame_{i:04d}_roi.txt")
                        mask = torch.from_numpy(load_roi_mask(roi_file, h, w))

                        r = psnr_masked(oy[i], dy[i], mask)
                        nr = psnr_masked(oy[i], dy[i], ~mask)

                        if not np.isnan(r):
                            roi_vals.append(r)
                        if not np.isnan(nr):
                            nonroi_vals.append(nr)

                    roi_psnr = np.mean(roi_vals)
                    nonroi_psnr = np.mean(nonroi_vals)

                    # ✅ WEIGHT AFTER AVERAGING (CORRECT)
                    avg_psnr = 0.7 * roi_psnr + 0.3 * nonroi_psnr

                    line = (
                        f"{method:<10} | {fname[:25]:<25} | {qp:<4} | "
                        f"{roi_psnr:8.2f} | {nonroi_psnr:10.2f} | {avg_psnr:12.2f}"
                    )
                    print(line)
                    f.write(line + "\n")

                    summary[method][qp].append(avg_psnr)

        # ---------------- SUMMARY ----------------
        f.write("\n" + "=" * 90 + "\n")
        f.write(f"{'SUMMARY: AVG PSNR (ROI 0.7 / nonROI 0.3)':^90}\n")
        f.write("=" * 90 + "\n")

        header = f"{'Method':<15}" + "".join([f"| QP{qp:<6}" for qp in TARGET_QPS])
        print("\n" + header)
        f.write(header + "\n")
        f.write("-" * 90 + "\n")

        for method in methods:
            row = f"{method:<15}"
            for qp in TARGET_QPS:
                vals = summary[method][qp]
                row += f"| {np.mean(vals):8.2f} " if vals else "|    -    "
            print(row)
            f.write(row + "\n")

    print(f"\nDONE! Results saved to {REPORT_FILE}")

# --------------------------------------------------
if __name__ == "__main__":
    main()
