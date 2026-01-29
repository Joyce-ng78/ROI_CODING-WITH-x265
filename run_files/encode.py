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

    ap.add_argument("--roi_method", type=str, default='motion', help='ROI method')
    ap.add_argument("--out", default="output/output_preset", help="Output directory")
    ap.add_argument("--qp", type=int, default=32, help="QP value for encoding")
    ap.add_argument("--enable_roi", type=int, default=1, help="enable roi")
    ap.add_argument("--openvino", type=int, default=1, help="choose cpu or inference mode")
    ap.add_argument("--fullresol", type=int, default=0, help="choose full resolution or not")
    ap.add_argument("--rc", type=int, default=2, help="choose CRF mode")
    ap.add_argument("--preset", type=str, default="veryfast", help="ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow, placebo")

    args = ap.parse_args()

    # os.makedirs(os.path.join(args.out, args.roi_method), exist_ok=True)
    input_path = 'input_yuv/class_B'
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
        preset = args.preset
        ROI_X265_BIN = "./roi_x265"
        roiname = args.roi_method
        outname = roiname
        if args.roi_method in ['yolov5', 'yolov8', 'yolov9', 'yolov10', 'yolov11']:
            if args.openvino:
                roiname += '_openvino'
            if args.fullresol:
                roiname += '_fullresol'
            # if preset:
            #     outname = roiname + f"_{preset}"
        
        roi_dir = os.path.join("roi", roiname, file_name)
        output = os.path.join(args.out,f"{roiname}_{preset}", f'qp{args.qp}')
        os.makedirs(output, exist_ok=True)
        output_hevc = os.path.join(output, f"{file_name}.bin")
        print(f"Processing {file_path}...")
        logfile = os.path.join('logs/logs_preset', f"{roiname}_{preset}", f'qp{args.qp}', f"{file_name}.txt")
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        print(roi_dir)
        print(output_hevc)
        print(logfile)
        
        cmd = [
            ROI_X265_BIN,
            "--input", file_path,
            "--output", output_hevc,
            "--width", str(width),
            "--preset", str(preset),
            "--height", str(height),
            "--fps", str(fps),
            "--qp", str(args.qp),
            "--roi-dir", roi_dir,
            "--enable-roi", f"{args.enable_roi}",
            "--print-log", "0",
            "--rc", str(args.rc)
        ]

        print("Running command encode:")
        with open(logfile, "w") as log_file:
            subprocess.run(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=True
            )
        cmd = [
            "./TAppDecoderStatic",
            "-b", output_hevc,
            "-o", os.path.join(output, f"{file_name}.yuv"),
        ]
        print('Running command decode:')
        with open(logfile, "a") as log_file:
            subprocess.run(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=True
            )

if __name__ == "__main__":
    main()
