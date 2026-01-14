import yolov5
import cv2
import numpy as np
import os
import argparse
import sys
import torch

# --- CONFIGURATION (defaults can be overridden via CLI) ---
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_FRAME_COUNT = 100
IOU_THRESHOLD = 0.3  # Threshold for merging overlapping boxes
# ---------------------

parser = argparse.ArgumentParser(description="Extract ROIs from a raw YUV420 (I420) file using YOLOv5")
parser.add_argument("--input", "-i", required=True, help="Input .yuv file path")
parser.add_argument("--width", "-W", type=int, default=DEFAULT_WIDTH, help="Frame width")
parser.add_argument("--height", "-H", type=int, default=DEFAULT_HEIGHT, help="Frame height")
parser.add_argument("--frames", "-n", type=int, default=DEFAULT_FRAME_COUNT, help="Number of frames to process")
parser.add_argument("--start", "-s", type=int, default=1, help="Start frame index (for output numbering)")
# UPDATED: Default output directory is now "roi"
parser.add_argument("--outdir", "-o", default="roi", help="Root output directory (default: roi)")
parser.add_argument("--framework", "-f", choices=["yolov5", "yolov8"], default="yolov5", help="Which model framework to use")
parser.add_argument("--model", "-m", default=None, help="Model path/name (default depends on framework)")
args = parser.parse_args()

WIDTH = args.width
HEIGHT = args.height
FRAME_COUNT = args.frames
START_IDX = args.start
INPUT_YUV = args.input
FRAMEWORK = args.framework
MODEL_PATH = args.model

if not os.path.exists(INPUT_YUV):
    print(f"Input file not found: {INPUT_YUV}", file=sys.stderr)
    sys.exit(1)

# --- FOLDER CREATION LOGIC ---
# 1. Get the video filename without extension (e.g. "BQTerrace_1920x1080_100")
video_name_stem = os.path.splitext(os.path.basename(INPUT_YUV))[0]

# 2. Join the root output dir ("roi") with the video name
# Result: roi/BQTerrace_1920x1080_100/
VIDEO_OUT_DIR = os.path.join(args.outdir, video_name_stem)

# 3. Create the directory
os.makedirs(VIDEO_OUT_DIR, exist_ok=True)
print(f"Output will be saved to: {VIDEO_OUT_DIR}")

# Output pattern uses 4 digits like frame_0001_roi.txt inside the video folder
OUTPUT_PATTERN = os.path.join(VIDEO_OUT_DIR, "frame_{:04d}_roi.txt")

# --- 1. Load YOLOv5 Model ---
print("Loading model...")
model = None
if FRAMEWORK == "yolov5":
    if MODEL_PATH is None:
        MODEL_PATH = "yolov5s.pt"
    try:
        # allow yolov5 Model class when unpickling
        try:
            import yolov5.models.yolo as _yolo_mod
            if hasattr(torch.serialization, "add_safe_globals"):
                torch.serialization.add_safe_globals([_yolo_mod.Model])
        except Exception:
            pass 

        model = yolov5.load(MODEL_PATH)
    except Exception as e:
        print("yolov5.load failed:", e, file=sys.stderr)
        print("Attempting fallback (ultralytics YOLO loader)...", file=sys.stderr)
        try:
            from ultralytics import YOLO
            model = YOLO(MODEL_PATH if os.path.exists(MODEL_PATH or "") else "yolov8n.pt")
            FRAMEWORK = "yolov8"
        except Exception as e2:
            print("Fallback to ultralytics failed:", e2, file=sys.stderr)
            sys.exit(1)
else:  # FRAMEWORK == "yolov8"
    try:
        from ultralytics import YOLO
    except Exception as e:
        print("ultralytics not installed:", e, file=sys.stderr)
        sys.exit(1)
    if MODEL_PATH is None:
        MODEL_PATH = "yolov8n.pt"
    try:
        model = YOLO(MODEL_PATH)
    except Exception as e:
        print("Failed to load yolov8 model:", e, file=sys.stderr)
        sys.exit(1)

# --- Helper Functions (Merge Logic) ---

def get_iou(box1, box2):
    """Calculate Intersection over Union (IoU) between two boxes."""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    xi1 = max(x1_1, x1_2)
    yi1 = max(y1_1, y1_2)
    xi2 = min(x2_1, x2_2)
    yi2 = min(y2_1, y2_2)
    
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - inter
    
    return inter / union if union > 0 else 0

def merge_overlapping_boxes(boxes, overlap_threshold=IOU_THRESHOLD):
    """
    Merge overlapping or stacked bounding boxes.
    """
    if len(boxes) == 0:
        return []
    
    merged = []
    used = [False] * len(boxes)
    
    for i in range(len(boxes)):
        if used[i]:
            continue
        
        x1, y1, x2, y2 = boxes[i]
        
        # Find overlapping boxes
        for j in range(i + 1, len(boxes)):
            if used[j]:
                continue
            
            if get_iou((x1, y1, x2, y2), boxes[j]) > overlap_threshold:
                # Merge boxes
                x1 = min(x1, boxes[j][0])
                y1 = min(y1, boxes[j][1])
                x2 = max(x2, boxes[j][2])
                y2 = max(y2, boxes[j][3])
                used[j] = True
        
        used[i] = True
        merged.append((x1, y1, x2, y2))
    
    return merged

def extract_detections(framework, model_obj, img_rgb):
    """Run detection and return Nx6 numpy (x1,y1,x2,y2,conf,cls)"""
    if framework == "yolov5":
        results = model_obj(img_rgb)
        try:
            dets = results.xyxy[0].cpu().numpy() if len(results.xyxy) > 0 else np.zeros((0,6))
        except Exception:
            dets = np.zeros((0,6))
        return dets
    else:  # yolov8 (ultralytics)
        res = model_obj(img_rgb)[0]
        if not hasattr(res, "boxes") or len(res.boxes) == 0:
            return np.zeros((0,6))
        xyxy = res.boxes.xyxy.cpu().numpy()
        conf = res.boxes.conf.cpu().numpy().reshape(-1,1)
        cls = res.boxes.cls.cpu().numpy().reshape(-1,1)
        return np.hstack([xyxy, conf, cls])

# --- Main Processing ---

# Calculate YUV buffer size for I420 (Y plane W*H, U and V each W*H/4)
frame_len = int(WIDTH * HEIGHT * 1.5)
rows = int(HEIGHT * 1.5)

print(f"Processing {FRAME_COUNT} frames from {INPUT_YUV} (W={WIDTH} H={HEIGHT})...")

with open(INPUT_YUV, 'rb') as f:
    for idx in range(START_IDX, START_IDX + FRAME_COUNT):
        yuv_data = f.read(frame_len)
        if len(yuv_data) < frame_len:
            print(f"End of file reached after {idx - START_IDX} frames.")
            break

        # Convert YUV to RGB
        yuv_arr = np.frombuffer(yuv_data, dtype=np.uint8).reshape((rows, WIDTH))
        img_bgr = cv2.cvtColor(yuv_arr, cv2.COLOR_YUV2BGR_I420)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # Run Detection
        detections = extract_detections(FRAMEWORK, model, img_rgb)

        # Convert detections to simple list of boxes for merging
        raw_boxes = []
        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            raw_boxes.append((int(x1), int(y1), int(x2), int(y2)))

        # Merge Overlapping Boxes
        merged_boxes = merge_overlapping_boxes(raw_boxes)

        # Write to ROI File (Output pattern now includes the subfolder)
        output_filename = OUTPUT_PATTERN.format(idx)
        with open(output_filename, 'w') as out_file:
            for box in merged_boxes:
                x1, y1, x2, y2 = box
                line = f"{x1}, {y1}, {x2}, {y2}\n"
                out_file.write(line)

        if (idx - START_IDX + 1) % 10 == 0:
            print(f"Generated {output_filename} (Boxes: {len(raw_boxes)} -> {len(merged_boxes)})")

print("Processing complete.")