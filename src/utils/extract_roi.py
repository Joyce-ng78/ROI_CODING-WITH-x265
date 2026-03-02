import os
import argparse
import numpy as np
import cv2
from tqdm import tqdm
from ultralytics import YOLO
import subprocess
import time
# ==============================
# YUV Reader
# ==============================
def read_yuv_frame(fp, w, h, idx):
    frame_size = w * h * 3 // 2
    fp.seek(idx * frame_size)
    y = np.fromfile(fp, np.uint8, w * h)
    return y.reshape((h, w))

def read_yuv420_frame(fp, w, h, idx):
    frame_size = w * h * 3 // 2
    fp.seek(idx * frame_size)

    y = np.fromfile(fp, np.uint8, w * h).reshape((h, w))
    u = np.fromfile(fp, np.uint8, w * h // 4).reshape((h//2, w//2))
    v = np.fromfile(fp, np.uint8, w * h // 4).reshape((h//2, w//2))

    u_up = cv2.resize(u, (w, h), interpolation=cv2.INTER_LINEAR)
    v_up = cv2.resize(v, (w, h), interpolation=cv2.INTER_LINEAR)

    yuv = cv2.merge([y, u_up, v_up])
    rgb = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB)

    return rgb, y

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
def round_up_32(x):
    return (x + 31) // 32 * 32
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
    ap.add_argument("--openvino", type=int, default=1)
    ap.add_argument("--fullresol", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(os.path.join(args.out, args.roi_method), exist_ok=True)
    input_path = 'input_yuv/class_B'
    if args.openvino:
        YOLO_WEIGHTS = {
            "yolov5":  "yolov5nu_openvino_model",    # nano (smallest)
            "yolov8":  "yolov8n_openvino_model",    # nano
            "yolov9":  "yolov9t_openvino_model",    # tiny
            "yolov10": "yolov10n_openvino_model",   # nano
            "yolov11": "yolo11n_openvino_model",   # nano (Ultralytics)
        }
    else:
        YOLO_WEIGHTS = {
            "yolov5":  "yolov5nu.pt",    # nano (smallest)
            "yolov8":  "yolov8n.pt",    # nano
            "yolov9":  "yolov9t.pt",    # tiny
            "yolov10": "yolov10n.pt",   # nano
            "yolov11": "yolo11n.pt",   # nano (Ultralytics)
        }
    
    roiname = args.roi_method
    if args.roi_method in ['yolov5', 'yolov8', 'yolov9', 'yolov10', 'yolov11']:
        model = YOLO(f'weights/{YOLO_WEIGHTS[args.roi_method]}', task='detect')
        print(f'Loaded pretrained weights/{YOLO_WEIGHTS[args.roi_method]}')
        
        if args.openvino:
            roiname += '_openvino'
        if args.fullresol:
            roiname += '_fullresol'
    
    out_roi = os.path.join(args.out, roiname)
        
    time_process = {}
    time_log = open("logs/time_extract_roi.txt", 'a')
    time_log.write(f"Extract roi with {roiname}\n")
    time_log.flush()
    print(f"Extract roi with {roiname}\n")
    
    
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
        import subprocess
        if args.fullresol:
            w32 = round_up_32(w)
            h32 = round_up_32(h)
            imgsz = [w32, h32]
        else:
            imgsz = 640
        

        os.makedirs(os.path.join(out_roi, file_name), exist_ok=True)
        seq_start = time.time()

        with open(file_path, "rb") as fp:
            prev = None
            for idx in tqdm(range(args.frames)):

                rgb, curr_y = read_yuv420_frame(fp, args.width, args.height, idx)
                rois = []
                if args.roi_method in ['motion', 'saliency', 'fused']:
                    # curr = read_yuv_frame(fp, args.width, args.height, idx)

                    roi_mask = np.zeros_like(curr_y, np.uint8)
                    
                    if args.roi_method in ["motion", "fused"] and prev is not None:
                        roi_mask |= motion_roi(prev, curr_y, args.block, args.t_motion)
                        rois = mask_to_bboxes(roi_mask, args.min_area)
                    if args.roi_method in ["saliency", "fused"]:
                        roi_mask |= saliency_roi(curr_y, args.t_saliency)
                        rois = mask_to_bboxes(roi_mask, args.min_area)
                    prev = curr_y.copy()
                else:
                    
                    results = model(
                        rgb,
                        imgsz=imgsz, 
                        conf=0.25,
                        iou=0.5,
                        half=True,     # FP16
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
                
                out_file = os.path.join(out_roi, file_name, f"frame_{idx:04d}_roi.txt")
                with open(out_file, "w") as f:
                    for x1,y1,x2,y2 in rois:
                        f.write(f"{x1}, {y1}, {x2}, {y2}\n")
                        
        seq_time = time.time() - seq_start

        time_process[file_name] = {
            "total_time": seq_time,
            "num_frames": args.frames,
            "avg_time_per_frame": seq_time / args.frames
        }

        # print(
        #     f"[{file_name}] "
        #     f"Total: {seq_time:.3f}s | "
        #     f"Avg/frame: {seq_time / args.frames * 1000:.2f} ms"
        # )
    all_seq_avg = np.mean([
        v["avg_time_per_frame"] for v in time_process.values()
    ])

    print("\n==== SUMMARY ====")
    for k, v in time_process.items():
        print(
            f"{k:30s} | "
            f"{v['avg_time_per_frame']*1000:.2f} ms/frame"
        )

    print(f"\nOverall average with {imgsz}: {all_seq_avg*1000:.2f} ms/frame")
    
    time_log.write(f'Overall average with {imgsz}: {all_seq_avg*1000:.2f} ms/frame\n')
    time_log.flush
                

if __name__ == "__main__":
    main()

