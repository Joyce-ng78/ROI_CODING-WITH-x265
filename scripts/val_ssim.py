import torch
import numpy as np
import os
import re
from torchmetrics.image import StructuralSimilarityIndexMeasure

# --- CONFIGURATION ---
INPUT_DIR = "./input_yuv/class_B"
OUTPUT_ROOT = "./output"
REPORT_FILE = "ssim_results.txt"
TARGET_QPS = [22, 27, 32, 37, 42, 47]

device = torch.device("cpu")

# --------------------------------------------------
# Read YUV420p (Y, U, V)
# --------------------------------------------------
def read_yuv_all_planes(path, w, h):
    y_size = w * h
    uv_w, uv_h = w // 2, h // 2
    uv_size = uv_w * uv_h
    frame_size = y_size + 2 * uv_size

    raw = np.fromfile(path, dtype=np.uint8)
    n_frames = raw.size // frame_size
    raw = raw.reshape(n_frames, frame_size)

    Y = raw[:, :y_size].reshape(n_frames, h, w)
    U = raw[:, y_size:y_size+uv_size].reshape(n_frames, uv_h, uv_w)
    V = raw[:, y_size+uv_size:].reshape(n_frames, uv_h, uv_w)

    return (
        torch.from_numpy(Y).float(),
        torch.from_numpy(U).float(),
        torch.from_numpy(V).float(),
        n_frames
    )

# --------------------------------------------------
# Parse resolution from filename
# --------------------------------------------------
def parse_filename(filename):
    m = re.search(r'(\d+)x(\d+)', filename)
    return (int(m.group(1)), int(m.group(2))) if m else (1920, 1080)

# --------------------------------------------------
# SSIM for video (torchmetrics)
# --------------------------------------------------
def calculate_ssim_video(video1, video2, data_range=255.0):
    """
    video: (N, H, W)
    """
    metric = StructuralSimilarityIndexMeasure(
        data_range=data_range
    ).to(device)

    ssim_vals = []

    for i in range(video1.shape[0]):
        x = video1[i].unsqueeze(0).unsqueeze(0).to(device)
        y = video2[i].unsqueeze(0).unsqueeze(0).to(device)
        ssim_vals.append(metric(x, y).item())

    return np.mean(ssim_vals)

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("Running SSIM evaluation (torchmetrics | YUV420p)")

    methods = sorted(
        d for d in os.listdir(OUTPUT_ROOT)
        if os.path.isdir(os.path.join(OUTPUT_ROOT, d))
    )

    summary_stats = {m: {qp: [] for qp in TARGET_QPS} for m in methods}

    with open(REPORT_FILE, "w") as f:
        header = (
            f"{'Method':<10} | {'Sequence':<25} | {'QP':<5} | "
            f"{'SSIM-Y':<10} | {'SSIM-U':<10} | {'SSIM-V':<10} | {'AVG-YUV':<10}"
        )
        print(header)
        f.write(header + "\n")
        f.write("-" * 100 + "\n")

        for method in methods:
            for qp in TARGET_QPS:
                qp_path = os.path.join(OUTPUT_ROOT, method, f"qp{qp}")
                if not os.path.exists(qp_path):
                    continue

                for filename in sorted(x for x in os.listdir(qp_path) if x.endswith(".yuv")):
                    org_path = os.path.join(INPUT_DIR, filename)
                    dec_path = os.path.join(qp_path, filename)

                    if not os.path.exists(org_path):
                        continue

                    w, h = parse_filename(filename)

                    oy, ou, ov, n1 = read_yuv_all_planes(org_path, w, h)
                    dy, du, dv, n2 = read_yuv_all_planes(dec_path, w, h)

                    n = min(n1, n2)

                    ssim_y = calculate_ssim_video(oy[:n], dy[:n])
                    ssim_u = calculate_ssim_video(ou[:n], du[:n])
                    ssim_v = calculate_ssim_video(ov[:n], dv[:n])

                    # YUV420 weighted SSIM
                    ssim_avg = (6 * ssim_y + ssim_u + ssim_v) / 8

                    line = (
                        f"{method:<10} | {filename[:25]:<25} | {qp:<5} | "
                        f"{ssim_y:10.6f} | {ssim_u:10.6f} | "
                        f"{ssim_v:10.6f} | {ssim_avg:10.6f}"
                    )

                    print(line)
                    f.write(line + "\n")
                    summary_stats[method][qp].append(ssim_avg)

        # SUMMARY
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"{'SUMMARY: AVG SSIM (YUV420)':^80}\n")
        f.write("=" * 80 + "\n")

        summary_header = f"{'Method':<15}" + "".join(
            [f"| QP{qp:<6}" for qp in TARGET_QPS]
        )
        print("\n" + summary_header)
        f.write(summary_header + "\n")
        f.write("-" * 80 + "\n")

        for method in methods:
            row = f"{method:<15}"
            for qp in TARGET_QPS:
                vals = summary_stats[method][qp]
                row += f"| {np.mean(vals):8.6f} " if vals else "|    -    "
            print(row)
            f.write(row + "\n")

    print(f"\nDONE! Results saved to {REPORT_FILE}")

# --------------------------------------------------
if __name__ == "__main__":
    main()
