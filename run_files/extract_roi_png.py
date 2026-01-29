import os
import argparse
import numpy as np
import cv2
from tqdm import tqdm
from ultralytics import YOLO

# ==============================
# PNG Reader
# ==============================
def read_png_frame_gray(frame_path):
    img = cv2.imread(frame_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Cannot read image: {frame_path}")
    return img


def read_png_frame_rgb(frame_path):
    img = cv2.imread(frame_path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Cannot read image: {frame_path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


# ==============================
# Motion-based ROI
# ==============================
def motion_roi(prev, curr, block, th):
    diff = cv2.absdiff(curr, prev)
    h, w = diff.shape

    mh = h // block
    mw = w // block
    motion_map = np.zeros((mh, mw), np.float32)

    for by in range(mh):
        for bx in range(mw):
            blk = diff[
                by * block:(by + 1) * block,
                bx * block:(bx + 1) * block
            ]
            motion_map[by, bx] = np.mean(blk)

    mask = (motion_map > th).astype(np.uint8)
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        np.ones((3, 3), np.uint8)
    )

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

    avg = cv2.blur(log_amp, (3, 3))
    residual = log_amp - avg

    sal = np.abs(
        np.fft.ifft2(np.exp(residual + 1j * phase))
    ) ** 2

    sal = cv2.GaussianBlur(sal, (9, 9), 0)
    sal = cv2.normalize(sal, None, 0, 1, cv2.NORM_MINMAX)
    return sal


def saliency_roi(gray, th):
    sal = spectral_residual(gray)
    mask = (sal > th).astype(np.uint8)

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        np.ones((5, 5), np.uint8)
    )
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
            rois.append((x, y, x + w, y + h))

    return rois


def overlap(a, b):
    return not (
        a[2] <= b[0] or
        a[0] >= b[2] or
        a[3] <= b[1] or
        a[1] >= b[3]
    )


def merge_two_boxes(a, b):
    return (
        min(a[0], b[0]),
        min(a[1], b[1]),
        max(a[2], b[2]),
        max(a[3], b[3])
    )


def merge_overlapping_rois(rois):
    rois = rois.copy()
    merged = True

    while merged:
        merged = False
        result = []

        while rois:
            current = rois.pop(0)
            i = 0
            while i < len(rois):
                if overlap(current, rois[i]):
                    current = merge_two_boxes(current, rois[i])
                    rois.pop(i)
                    merged = True
                else:
                    i += 1
            result.append(current)

        rois = result

    return rois


# ==============================
# Main
# ==============================
def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--roi_method", type=str, default="motion",
                    choices=["motion", "saliency", "fused",
                             "yolov5", "yolov8", "yolov9",
                             "yolov10", "yolov11"])
    ap.add_argument("--block", type=int, default=32)
    ap.add_argument("--t_motion", type=float, default=35.0)
    ap.add_argument("--t_saliency", type=float, default=0.15)
    ap.add_argument("--min_area", type=int, default=256)
    ap.add_argument("--out", default="roi")
    args = ap.parse_args()

    input_path = "input_img/class_B"
    os.makedirs(os.path.join(args.out, args.roi_method), exist_ok=True)

    # ================= YOLO =================
    YOLO_WEIGHTS = {
        "yolov5":  "yolov5n.pt",
        "yolov8":  "yolov8n.pt",
        "yolov9":  "yolov9t.pt",
        "yolov10": "yolov10n.pt",
        "yolov11": "yolo11n.pt",
    }

    model = None
    if args.roi_method in YOLO_WEIGHTS:
        model = YOLO(f"weights/{YOLO_WEIGHTS[args.roi_method]}")
        print(f"[INFO] Loaded YOLO weights: {YOLO_WEIGHTS[args.roi_method]}")

    # ================= Process sequences =================
    for seq in os.listdir(input_path):
        seq_path = os.path.join(input_path, seq)
        if not os.path.isdir(seq_path):
            continue

        frame_list = sorted(
            f for f in os.listdir(seq_path)
            if f.endswith(".png")
        )
        if len(frame_list) == 0:
            continue

        print(f"[INFO] Processing {seq} ({len(frame_list)} frames)")
        out_dir = os.path.join(args.out, args.roi_method, seq)
        os.makedirs(out_dir, exist_ok=True)

        prev = None

        for idx, fname in enumerate(tqdm(frame_list)):
            frame_path = os.path.join(seq_path, fname)
            rois = []

            # ===== Motion / Saliency =====
            if args.roi_method in ["motion", "saliency", "fused"]:
                curr = read_png_frame_gray(frame_path)
                roi_mask = np.zeros_like(curr, np.uint8)

                if args.roi_method in ["motion", "fused"] and prev is not None:
                    roi_mask |= motion_roi(
                        prev, curr, args.block, args.t_motion
                    )

                if args.roi_method in ["saliency", "fused"]:
                    roi_mask |= saliency_roi(curr, args.t_saliency)

                rois = mask_to_bboxes(roi_mask, args.min_area)
                prev = curr.copy()

            # ===== YOLO =====
            else:
                print(frame_path)
                # rgb = read_png_frame_rgb(frame_path)
                results = model(
                    frame_path,
                    imgsz=640,
                    conf=0.25,
                    iou=0.5,
                    half=True,
                    verbose=False
                )

                for r in results:
                    if r.boxes is None:
                        continue
                    boxes = r.boxes.xyxy.cpu().numpy()
                    for x1, y1, x2, y2 in boxes:
                        rois.append((
                            int(x1), int(y1),
                            int(x2), int(y2)
                        ))

            rois = merge_overlapping_rois(rois)

            # out_file = os.path.join(
            #     out_dir,
            #     f"frame_{idx:04d}_roi.txt"
            # )
            # with open(out_file, "w") as f:
            #     for x1, y1, x2, y2 in rois:
            #         f.write(f"{x1}, {y1}, {x2}, {y2}\n")


if __name__ == "__main__":
    main()
