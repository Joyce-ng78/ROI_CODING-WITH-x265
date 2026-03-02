import subprocess
import os
import argparse


# ==============================
# Argument parsing
# ==============================
def parse_args():
    ap = argparse.ArgumentParser()

    ap.add_argument("--encode_path", type=str, default="build/roi_x265")
    ap.add_argument("--decode_path", type=str, default="build/TAppDecoderStatic")

    ap.add_argument("--input_root", type=str, default="data/raw_yuv/class_B")

    ap.add_argument("--roi_root", type=str, default="data/roi_extraction")
    ap.add_argument("--roi_method", type=str, default="motion")

    ap.add_argument("--out", default="outputs/output_preset")
    ap.add_argument("--logs", default="logs/logs_preset")

    ap.add_argument("--qp", type=int, default=32)
    ap.add_argument("--enable_roi", type=int, default=1)
    ap.add_argument("--rc", type=int, default=2)
    ap.add_argument("--preset", type=str, default="medium")
    ap.add_argument("--fps", type=int, default=15)

    ap.add_argument("--rd_level", type=int, default=1)
    ap.add_argument("--rdoq_level", type=int, default=0)
    ap.add_argument("--psy_rd", type=float, default=2.0)

    return ap.parse_args()


# ==============================
# Sequence info parsing
# ==============================
def parse_sequence_info(filename):
    """
    filename format: name_WIDTHxHEIGHT_FRAMES.yuv
    """
    name = filename.split(".")[0]
    _, wxh, nfs = name.split("_")

    width, height = map(int, wxh.split("x"))
    frames = int(nfs)

    return name, width, height, frames


# ==============================
# Command builders
# ==============================
def build_encode_cmd(args, output_hevc, roi_dir,
                     width, height, fps):
    return [
        args.encode_path,
        "--input", args.input_root,
        "--output", output_hevc,
        "--width", str(width),
        "--height", str(height),
        "--fps", str(fps),
        "--preset", args.preset,
        "--qp", str(args.qp),
        "--roi-dir", roi_dir,
        "--enable-roi", str(args.enable_roi),
        "--rc", str(args.rc),
        "--fps", str(args.fps),
        "--rd_level", str(args.rd_level),
        "--rdoq_level", str(args.rdoq_level),
        "--psy_rd", str(args.psy_rd)
    ]


def build_decode_cmd(args, bitstream, output_yuv):
    return [
        args.decode_path,
        "-b", bitstream,
        "-o", output_yuv,
    ]


# ==============================
# Run command
# ==============================
def run_command(cmd, logfile, mode="w"):
    print("Running:")
    print(" ".join(cmd))

    with open(logfile, mode) as f:
        subprocess.run(
            cmd,
            stdout=f,
            stderr=subprocess.STDOUT,
            check=True
        )


# ==============================
# Main
# ==============================
def main():
    args = parse_args()

    fps = args.fps

    for seq in os.listdir(args.input_root):
        input_path = os.path.join(args.input_root, seq)

        name, width, height, frames = parse_sequence_info(seq)

        roi_dir = os.path.join(
            args.roi_root,
            args.roi_method,
            name
        )

        method_name = (
            f"{args.roi_method}_preset_{args.preset}_rdo_{args.rd_level}"
        )

        output_dir = os.path.join(
            args.out,
            method_name,
            f"qp{args.qp}"
        )
        os.makedirs(output_dir, exist_ok=True)

        log_dir = os.path.join(
            args.logs,
            method_name,
            f"qp{args.qp}"
        )
        os.makedirs(log_dir, exist_ok=True)

        output_hevc = os.path.join(output_dir, f"{name}.bin")
        output_yuv = os.path.join(output_dir, f"{name}.yuv")
        logfile = os.path.join(log_dir, f"{name}.txt")

        print(f"\n=== Processing {name} ===")

        # Encode
        encode_cmd = build_encode_cmd(
            args,
            input_path,
            output_hevc,
            roi_dir,
            width,
            height,
            fps 
        )
        run_command(encode_cmd, logfile, mode="w")

        # Decode
        decode_cmd = build_decode_cmd(
            args,
            output_hevc,
            output_yuv
        )
        run_command(decode_cmd, logfile, mode="a")


if __name__ == "__main__":
    main()
