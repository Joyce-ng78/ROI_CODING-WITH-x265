import torch
import numpy as np
import os
import re

# --- CONFIGURATION ---
INPUT_DIR = "./input_yuv/class_B"
OUTPUT_ROOT = "./output_RCF"
REPORT_FILE = "psnr_results.txt"
TARGET_QPS = [22, 27, 32, 37, 42, 47]

# --------------------------------------------------
# Read YUV420p (Y, U, V)
# --------------------------------------------------
def read_yuv_all_planes(file_path, width, height, num_frames=None):
    if not os.path.exists(file_path):
        return None, None, None

    y_size = width * height
    uv_width = width // 2
    uv_height = height // 2
    uv_size = uv_width * uv_height
    frame_size = y_size + 2 * uv_size

    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()

        total_frames = len(raw_data) // frame_size
        if num_frames is not None:
            total_frames = min(total_frames, num_frames)

        y_data, u_data, v_data = [], [], []

        for i in range(total_frames):
            frame_start = i * frame_size

            # Y
            y = np.frombuffer(
                raw_data, dtype=np.uint8,
                count=y_size, offset=frame_start
            ).reshape((height, width))

            # U
            u_start = frame_start + y_size
            u = np.frombuffer(
                raw_data, dtype=np.uint8,
                count=uv_size, offset=u_start
            ).reshape((uv_height, uv_width))

            # V (FIXED OFFSET)
            v_start = u_start + uv_size
            v = np.frombuffer(
                raw_data, dtype=np.uint8,
                count=uv_size, offset=v_start
            ).reshape((uv_height, uv_width))

            y_data.append(y)
            u_data.append(u)
            v_data.append(v)

        return (
            torch.tensor(np.array(y_data), dtype=torch.float32),
            torch.tensor(np.array(u_data), dtype=torch.float32),
            torch.tensor(np.array(v_data), dtype=torch.float32)
        )

    except Exception:
        return None, None, None

# --------------------------------------------------
# PSNR
# --------------------------------------------------
def calculate_psnr(original, decoded):
    mse = torch.mean((original - decoded) ** 2)
    if mse == 0:
        return 100.0
    return (20 * torch.log10(255.0 / torch.sqrt(mse))).item()

# --------------------------------------------------
# Parse resolution from filename
# --------------------------------------------------
def parse_filename(filename):
    match = re.search(r'(\d+)x(\d+)', filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 1920, 1080

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("Running PSNR evaluation (YUV420p)")

    methods = [
        d for d in os.listdir(OUTPUT_ROOT)
        if os.path.isdir(os.path.join(OUTPUT_ROOT, d))
    ]
    methods.sort()

    summary_stats = {m: {qp: [] for qp in TARGET_QPS} for m in methods}

    with open(REPORT_FILE, "w") as f:
        header = (
            f"{'Method':<30} | {'Sequence':<25} | {'QP':<5} | "
            f"{'PSNR-Y':<10} | {'PSNR-U':<30} | {'PSNR-V':<30} | {'AVG-YUV':<30}"
        )
        print(header)
        f.write(header + "\n")
        f.write("-" * 100 + "\n")

        for method in methods:
            method_path = os.path.join(OUTPUT_ROOT, method)

            for qp in TARGET_QPS:
                qp_path = os.path.join(method_path, f"qp{qp}")
                if not os.path.exists(qp_path):
                    continue

                decoded_files = sorted(
                    x for x in os.listdir(qp_path) if x.endswith(".yuv")
                )

                for filename in decoded_files:
                    org_path = os.path.join(INPUT_DIR, filename)
                    dec_path = os.path.join(qp_path, filename)

                    if not os.path.exists(org_path):
                        continue

                    width, height = parse_filename(filename)

                    org_y, org_u, org_v = read_yuv_all_planes(org_path, width, height)
                    dec_y, dec_u, dec_v = read_yuv_all_planes(dec_path, width, height)

                    if org_y is None or dec_y is None:
                        continue

                    min_frames = min(org_y.shape[0], dec_y.shape[0])

                    p_y = calculate_psnr(org_y[:min_frames], dec_y[:min_frames])
                    p_u = calculate_psnr(org_u[:min_frames], dec_u[:min_frames])
                    p_v = calculate_psnr(org_v[:min_frames], dec_v[:min_frames])

                    # YUV420 WEIGHTED AVERAGE (CORRECT)
                    p_avg = (6 * p_y + p_u + p_v) / 8

                    line = (
                        f"{method:<10} | {filename[:25]:<25} | {qp:<5} | "
                        f"{p_y:10.4f} | {p_u:10.4f} | {p_v:10.4f} | {p_avg:10.4f}"
                    )

                    print(line)
                    f.write(line + "\n")

                    summary_stats[method][qp].append(p_avg)

        # SUMMARY
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"{'SUMMARY: AVG PSNR (YUV420)':^80}\n")
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
                if vals:
                    row += f"| {sum(vals)/len(vals):8.4f} "
                else:
                    row += f"| {'-':<8} "
            print(row)
            f.write(row + "\n")

    print(f"\nDONE! Results saved to {REPORT_FILE}")

# --------------------------------------------------
if __name__ == "__main__":
    main()
