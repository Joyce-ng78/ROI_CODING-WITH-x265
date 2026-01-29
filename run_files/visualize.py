import os
import argparse
import numpy as np
import cv2
from tqdm import tqdm
from ultralytics import YOLO
# ==============================
# YUV Reader
# ==============================
def read_yuv_frame(fp, w, h, idx):
    frame_size = w * h * 3 // 2
    fp.seek(idx * frame_size)
    y = np.fromfile(fp, np.uint8, w * h)
    return y.reshape((h, w))

# def read_yuv420_frame(fp, w, h, idx):
#     frame_size = w * h * 3 // 2
#     fp.seek(idx * frame_size)

#     y = np.fromfile(fp, np.uint8, w * h).reshape((h, w))
#     u = np.fromfile(fp, np.uint8, w * h // 4).reshape((h//2, w//2))
#     v = np.fromfile(fp, np.uint8, w * h // 4).reshape((h//2, w//2))

#     u_up = cv2.resize(u, (w, h), interpolation=cv2.INTER_LINEAR)
#     v_up = cv2.resize(v, (w, h), interpolation=cv2.INTER_LINEAR)

#     yuv = cv2.merge([y, u_up, v_up])
#     rgb = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB)

#     return rgb, y
def read_yuv420_frame(fp, w, h, idx):
    frame_size = w * h * 3 // 2
    fp.seek(idx * frame_size)

    yuv = np.fromfile(fp, np.uint8, frame_size)
    yuv = yuv.reshape((h * 3 // 2, w))

    rgb = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB_I420)
    y = yuv[:h, :]   # Y plane

    return rgb, y


def read_rois_from_txt(txt_path):
    rois = []
    with open(txt_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            x1, y1, x2, y2 = map(int, line.split(','))
            rois.append((x1, y1, x2, y2))
    return rois
import cv2

def draw_rois(image, rois, color=(0, 255, 0), thickness=2):
    for (x1, y1, x2, y2) in rois:
        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
    return image

# ==============================
# Main
# ==============================
def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--roi_method", type=str, default='motion', help='ROI method')
    ap.add_argument("--block", type=int, default=32)
    ap.add_argument("--t_motion", type=float, default=35.0)
    ap.add_argument("--t_saliency", type=float, default=0.15)
    ap.add_argument("--min_area", type=int, default=256)
    ap.add_argument("--out", default="roi")
    args = ap.parse_args()

    os.makedirs(os.path.join(args.out, args.roi_method), exist_ok=True)
    input_path = 'input_yuv/class_B'
    output_vis = 'visualize'
    

    for  roi_method in ['saliency',  'motion']:
        for seq in os.listdir(input_path):
            file_path = os.path.join(input_path, seq)
            file_name = seq.split('.')[0]
            _, wxh, nfs = file_name.split('_')
            nfs = int(nfs)
            w, h = int(wxh.split('x')[0]), int(wxh.split('x')[1])
            print(f"Processing {file_path} with {roi_method}...")
            out_folder = f'{output_vis}/{roi_method}/{seq[:-4]}'
            os.makedirs(out_folder, exist_ok=True)
            with open(file_path, "rb") as fp:
                prev = None

                for idx in tqdm(range(nfs)):

                    rois = []
                    rgb, curr_y = read_yuv420_frame(fp, w, h, idx)

                    roi_txt = f'roi/{roi_method}/{seq[:-4]}/frame_{idx:04d}_roi.txt'

                    if not os.path.exists(roi_txt):
                        print(f'Roi file {roi_txt} does not exist!\n')
                        continue

                    # 1. đọc ROI
                    rois = read_rois_from_txt(roi_txt)

                    # 2. vẽ ROI lên ảnh
                    rgb_drawn = draw_rois(rgb.copy(), rois)

                    # 3. hiển thị hoặc lưu
                    # cv2.imshow("ROI", rgb_drawn)
                    # cv2.waitKey(1)
                    # hoặc:
                    out_path = f'{out_folder}/frame_{idx:04d}.png'
                    # print(out_path)
                    bgr_save = cv2.cvtColor(rgb_drawn, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(out_path, bgr_save)
                    
                

if __name__ == "__main__":
    main()

