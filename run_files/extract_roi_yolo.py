import os
import argparse
import time
import subprocess
import numpy as np
import cv2
from tqdm import tqdm
from ultralytics import YOLO

# ==============================
# FFmpeg extract frames
# ==============================
def extract_frames_ffmpeg(yuv_path, out_dir, w, h, nframes):
    if os.path.exists(out_dir) and len(os.listdir(out_dir)) >= nframes:
        return

    os.makedirs(out_dir, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "yuv420p",
        "-s", f"{w}x{h}",
        "-i", yuv_path,
        "-frames:v", str(nframes),
        f"{out_dir}/frame_%04d.png"
    ]
    subprocess.run(cmd, check=True)


# ==============================
# Image readers
# ==============================
def read_gray_img(path):
    return cv2.imread(path, cv2.IMREAD_GRAYSCALE)

def read_rgb_img(path):
    return cv2.imread(path, cv2.IMREAD_COLOR)[:, :, ::-1]


# ==============================
# Motion-based ROI
# ==============================
def motion_roi(prev, curr, block, th):
    diff = cv2.absdiff(curr, prev)
    h, w = diff.shape

    mh, mw = h // block, w // block
    motion_map = np.zeros((mh, mw), np.float32)

    for y in range(mh):
        for x in range(mw):
            blk = diff[y*block:(y+1)*block, x*block:(x+1)*block]
            motion_map[y, x] = np.mean(blk)

    mask = (motion_map > th).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8))
    mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
    return mask


# ==============================
# Saliency (Spectral Residual)
# ==============================
def spectral_residual(gray):
    gray = gray.astype(np.float32)
    fft = np.fft.fft2(gray)
    log_amp = np.log(np.abs(fft) + 1e-8)
    phase = np.angle(fft)

    avg = cv2.blur(log_amp, (3,3))
    residual = log_amp - avg

    sal = np.abs(np.fft.ifft2(np.exp(residual + 1j * phase))) ** 2
    sal = cv2.GaussianBlur(sal, (9,9), 0)
    sal = cv2.normalize(sal, None, 0, 1, cv2.NORM_MINMAX)
    return sal

def saliency_roi(gray, th):
    sal = spectral_residual(gray)
    mask = (sal > th).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
    return mask


# ==============================
# Mask → ROI boxes
# ==============================
def mask_to_bboxes(mask, min_area):
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    rois = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area >= min_area:
            rois.append((x, y, x+w, y+h))
    return rois

def overlap(a, b):
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])

def merge_two_boxes(a, b):
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))

def merge_overlapping_rois(rois):
    rois = rois.copy()
    merged = True
    while merged:
        merged = False
        result = []
        while rois:
            cur = rois.pop(0)
            i = 0
            while i < len(rois):
                if overlap(cur, rois[i]):
                    cur = merge_two_boxes(cur, rois[i])
                    rois.pop(i)
                    merged = True
                else:
                    i += 1
            result.append(cur)
        rois = result
    return rois


# ==============================
# Main
# ==============================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roi_method", default="motion",
                    choices=["motion", "saliency", "fused",
                             "yolov5", "yolov8", "yolov9", "yolov10", "yolov11"])
    ap.add_argument("--block", type=int, default=32)
    ap.add_argument("--t_motion", type=float, default=35.0)
    ap.add_argument("--t_saliency", type=float, default=0.15)
    ap.add_argument("--min_area", type=int, default=256)
    ap.add_argument("--out", default="roi")
    args = ap.parse_args()

    input_path = "input_yuv/class_B"
    input_img = "input_img/class_B"

    YOLO_WEIGHTS = {
        "yolov5":  "yolov5n.pt",
        "yolov8":  "yolov8n.pt",
        "yolov9":  "yolov9t.pt",
        "yolov10": "yolov10n.pt",
        "yolov11": "yolo11n.pt",
    }

    model = None
    if args.roi_method.startswith("yolo"):
        model = YOLO(f"weights/{YOLO_WEIGHTS[args.roi_method]}")

    for seq in os.listdir(input_path):
        yuv_path = os.path.join(input_path, seq)
        name = seq.split(".")[0]
        _, wxh, nfs = name.split("_")
        w, h = map(int, wxh.split("x"))
        nfs = int(nfs)

        img_dir = os.path.join(input_img, name)

        print(f"\n▶ Extract frames: {name}")
        extract_frames_ffmpeg(yuv_path, img_dir, w, h, nfs)

        out_dir = os.path.join(args.out, args.roi_method, name)
        os.makedirs(out_dir, exist_ok=True)

        prev = None
        start = time.time()

        for i in tqdm(range(nfs)):
            img_path = os.path.join(img_dir, f"frame_{i+1:04d}.png")
            rois = []

            if args.roi_method in ["motion", "saliency", "fused"]:
                curr = read_gray_img(img_path)
                mask = np.zeros_like(curr, np.uint8)

                if args.roi_method in ["motion", "fused"] and prev is not None:
                    mask |= motion_roi(prev, curr, args.block, args.t_motion)

                if args.roi_method in ["saliency", "fused"]:
                    mask |= saliency_roi(curr, args.t_saliency)

                rois = mask_to_bboxes(mask, args.min_area)
                prev = curr.copy()

            else:
                rgb = read_rgb_img(img_path)
                results = model(rgb, imgsz=640, conf=0.25, iou=0.5, verbose=False)
                for r in results:
                    if r.boxes is None:
                        continue
                    for x1, y1, x2, y2 in r.boxes.xyxy.cpu().numpy():
                        rois.append((int(x1), int(y1), int(x2), int(y2)))

            rois = merge_overlapping_rois(rois)

            with open(os.path.join(out_dir, f"frame_{i:04d}_roi.txt"), "w") as f:
                for x1, y1, x2, y2 in rois:
                    f.write(f"{x1},{y1},{x2},{y2}\n")

        elapsed = time.time() - start
        fps = nfs / elapsed
        tpf = elapsed / nfs

        print(f"\n✅ Method: {args.roi_method}")
        print(f"   Total time : {elapsed:.2f}s")
        print(f"   FPS        : {fps:.2f}")
        print(f"   Time/frame : {tpf*1000:.2f} ms")


if __name__ == "__main__":
    main()
