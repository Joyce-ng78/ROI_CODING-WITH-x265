import os
import argparse
import numpy as np
import cv2
from tqdm import tqdm

# ==============================
# YUV Reader
# ==============================
def read_yuv_frame(fp, w, h, idx):
    frame_size = w * h * 3 // 2
    fp.seek(idx * frame_size)
    y = np.fromfile(fp, np.uint8, w * h)
    return y.reshape((h, w))

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
                by*block:(by+1)*block,
                bx*block:(bx+1)*block
            ]
            motion_map[by, bx] = np.mean(blk)

    mask = (motion_map > th).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                             np.ones((3,3), np.uint8))
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

    sal = np.abs(
        np.fft.ifft2(np.exp(residual + 1j * phase))
    ) ** 2

    sal = cv2.GaussianBlur(sal, (9,9), 0)
    sal = cv2.normalize(sal, None, 0, 1, cv2.NORM_MINMAX)
    return sal

def saliency_roi(frame, th):
    sal = spectral_residual(frame)
    mask = (sal > th).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                             np.ones((5,5), np.uint8))
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
    return not (
        a[2] <= b[0] or  # A bên trái B
        a[0] >= b[2] or  # A bên phải B
        a[3] <= b[1] or  # A phía trên B
        a[1] >= b[3]     # A phía dưới B
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

    ap.add_argument("--mode", choices=["motion","saliency","fused"], required=True)
    ap.add_argument("--block", type=int, default=32)
    ap.add_argument("--t_motion", type=float, default=35.0)
    ap.add_argument("--t_saliency", type=float, default=0.15)
    ap.add_argument("--min_area", type=int, default=256)
    ap.add_argument("--out", default="roi")
    args = ap.parse_args()

    os.makedirs(os.path.join(args.out, args.mode), exist_ok=True)
    input_path = 'input_yuv\class_B'
    for seq in os.listdir(input_path):
        file_path = os.path.join(input_path, seq)
        file_name = seq.split('.')[0]
        _, wxh, nfs = file_name.split('_')
        nfs = int(nfs)
        w, h = int(wxh.split('x')[0]), int(wxh.split('x')[1])
        args.width = w
        args.height = h
        args.frames = nfs
        print(f"Processing {file_path}...")
        with open(file_path, "rb") as fp:
            prev = None

            for idx in tqdm(range(args.frames)):

                curr = read_yuv_frame(fp, args.width, args.height, idx)

                roi_mask = np.zeros_like(curr, np.uint8)

                if args.mode in ["motion", "fused"] and prev is not None:
                    roi_mask |= motion_roi(prev, curr, args.block, args.t_motion)

                if args.mode in ["saliency", "fused"]:
                    roi_mask |= saliency_roi(curr, args.t_saliency)

                rois = mask_to_bboxes(roi_mask, args.min_area)
                rois = merge_overlapping_rois(rois)

                os.makedirs(os.path.join(args.out, args.mode, file_name), exist_ok=True)
                out_file = os.path.join(args.out, args.mode, file_name, f"frame_{idx:04d}.txt")
                with open(out_file, "w") as f:
                    # f.write(f"{len(rois)}\n")
                    for x1,y1,x2,y2 in rois:
                        f.write(f"{x1} {y1} {x2} {y2}\n")

                prev = curr.copy()

if __name__ == "__main__":
    main()
