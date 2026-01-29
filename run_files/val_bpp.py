import os
import re
from collections import defaultdict

# ================= CONFIG =================
OUTPUT_ROOT = "./output_RCF"
RESULT_FILE = "results_bpp.txt"
TARGET_QPS = [22, 27, 32, 37, 42, 47]

# ================= PARSE INFO FROM NAME =================
def parse_info(filename):
    """
    Example: BasketballDrive_1920x1080_100.bin
    """
    m = re.search(r"(.+?)_(\d+)x(\d+)_(\d+)", filename)
    if not m:
        return None

    seq = m.group(1)
    w = int(m.group(2))
    h = int(m.group(3))
    frames = int(m.group(4))

    return seq, w, h, frames

# ================= MAIN =================
def main():
    methods = sorted([
        d for d in os.listdir(OUTPUT_ROOT)
        if os.path.isdir(os.path.join(OUTPUT_ROOT, d))
    ])

    # results[sequence][qp][method] = bpp
    results = defaultdict(lambda: defaultdict(dict))

    with open(RESULT_FILE, "w") as f:
        print("Calculating BPP from .bin files\n")

        for method in methods:
            for qp in TARGET_QPS:
                qp_dir = os.path.join(OUTPUT_ROOT, method, f"qp{qp}")
                if not os.path.exists(qp_dir):
                    continue

                for fname in os.listdir(qp_dir):
                    if not fname.endswith(".bin"):
                        continue

                    info = parse_info(fname)
                    if info is None:
                        continue

                    seq, w, h, frames = info
                    bin_path = os.path.join(qp_dir, fname)

                    file_size_bytes = os.path.getsize(bin_path)
                    bits = file_size_bytes * 8

                    bpp = bits / (w * h * frames)

                    results[seq][qp][method] = bpp

        # ================= PRINT TABLE =================
        f.write("=" * 120 + "\n")
        f.write("SUMMARY BPP TABLE (ROWS: SEQUENCE + QP, COLS: METHODS)\n")
        f.write("=" * 120 + "\n")

        header = f"{'Sequence':<20}|{'QP':<4}"
        for m in methods:
            header += f"|{m:<12}"
        print(header)
        f.write(header + "\n")
        f.write("-" * 120 + "\n")

        for seq in sorted(results.keys()):
            for qp in TARGET_QPS:
                row = f"{seq:<20}|{qp:<4}"
                for m in methods:
                    val = results[seq].get(qp, {}).get(m, None)
                    row += f"|{val:12.6f}" if val is not None else f"|{'-':<12}"
                print(row)
                f.write(row + "\n")
        # ================= SUMMARY =================
        f.write("=" * 120 + "\n")
        f.write("SUMMARY BPP (AVERAGE PER SEQUENCE)\n")
        f.write("=" * 120 + "\n")
        summary_row = f"{'Average BPP':<20}|{'ALL':<4}"
        for m in methods:
            bpp_values = []
            for seq in results.keys():
                for qp in TARGET_QPS:
                    val = results[seq].get(qp, {}).get(m, None)
                    if val is not None:
                        bpp_values.append(val)
            avg_bpp = sum(bpp_values) / len(bpp_values) if bpp_values else 0
            summary_row += f"|{avg_bpp:12.6f}"
        print(summary_row)
        f.write(summary_row + "\n")    
        


    print(f"\nDONE ✔ BPP results saved to {RESULT_FILE}")

# ================= RUN =================
if __name__ == "__main__":
    main()
