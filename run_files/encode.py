import subprocess
import os
import argparse
import numpy as np
import cv2
from tqdm import tqdm

# ==============================
# Main
# ==============================
def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--mode", type=str, default='motion', help='ROI method')
    ap.add_argument("--out", default="output", help="Output directory")
    ap.add_argument("--qp", type=int, default=32, help="QP value for encoding")
    args = ap.parse_args()

    os.makedirs(os.path.join(args.out, args.mode), exist_ok=True)
    input_path = 'input_yuv\class_B'
    for seq in os.listdir(input_path):
        file_path = os.path.join(input_path, seq)
        file_name = seq.split('.')[0]
        _, wxh, nfs = file_name.split('_')
        nfs = int(nfs)
        w, h = int(wxh.split('x')[0]), int(wxh.split('x')[1])
        width = w
        height = h
        frames = nfs
        fps = 15

        ROI_X265_BIN = "./roi_x265"
        roi_dir = os.path.join("roi", args.mode, f'qp{args.qp}', file_name)
        output = os.path.join(args.out, args.mode, f'qp{args.qp}')
        os.makedirs(output, exist_ok=True)
        output_hevc = os.path.join(output, f"{file_name}.bin")
        print(f"Processing {file_path}...")
        logfile = os.path.join('logs', args.mode, f'qp{args.qp}', f"{file_name}.txt")
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        print(roi_dir)
        print(output_hevc)
        print(logfile)
        
        cmd = [
            ROI_X265_BIN,
            "--input", file_path,
            "--output", output_hevc,
            "--width", str(width),
            "--height", str(height),
            "--fps", str(fps),
            "--qp", str(args.qp),
            "--roi-dir", roi_dir,
            "--enable-roi", "1",
            "--print-log", "0",
        ]

        print("Running command:")
        with open(logfile, "w") as log_file:
            subprocess.run(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=True
            )
if __name__ == "__main__":
    main()
