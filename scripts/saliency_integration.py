

import numpy as np
import cv2
from scipy.ndimage import gaussian_filter
import argparse
from pathlib import Path


# ──────────────────────────────────────────────
# 1. VISUAL SALIENCY MODEL — Spectral Residual
# ──────────────────────────────────────────────
def compute_saliency_SR(image_bgr: np.ndarray) -> np.ndarray:
    """
    Tính saliency map bằng Spectral Residual (SR).
    Input : BGR image uint8
    Output: saliency map float32, cùng kích thước, giá trị [0,1]
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # Resize về 64x64 để tính nhanh, sau đó resize lại
    h, w = gray.shape
    small = cv2.resize(gray, (64, 64))

    # FFT
    f = np.fft.fft2(small)
    log_amplitude = np.log(np.abs(f) + 1e-8)
    phase = np.angle(f)

    # Spectral residual = log_amplitude - smoothed_log_amplitude
    smooth = gaussian_filter(log_amplitude, sigma=3)
    residual = log_amplitude - smooth

    # Reconstruct saliency
    f_residual = np.exp(residual) * np.exp(1j * phase)
    saliency_small = np.abs(np.fft.ifft2(f_residual)) ** 2
    saliency_small = gaussian_filter(saliency_small, sigma=5)

    # Resize về kích thước gốc
    saliency = cv2.resize(saliency_small, (w, h))

    # Normalize về [0, 1]
    saliency = (saliency - saliency.min()) / (saliency.max() - saliency.min() + 1e-8)
    return saliency.astype(np.float32)


# ──────────────────────────────────────────────
# 2. LOCAL DISTORTION MAP — SSIM-based
# ──────────────────────────────────────────────
def compute_distortion_map(ref_bgr: np.ndarray,
                            dist_bgr: np.ndarray,
                            window_size: int = 11) -> np.ndarray:
    """
    Tính local distortion map D(x,y) = 1 - SSIM_local(x,y).
    Giá trị cao = nhiễu loạn nhiều.
    """
    ref_gray  = cv2.cvtColor(ref_bgr,  cv2.COLOR_BGR2GRAY).astype(np.float32)
    dist_gray = cv2.cvtColor(dist_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2
    sigma = 1.5

    # Gaussian weighted local statistics
    def gf(x): return gaussian_filter(x, sigma=sigma)

    mu1   = gf(ref_gray)
    mu2   = gf(dist_gray)
    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = gf(ref_gray  ** 2) - mu1_sq
    sigma2_sq = gf(dist_gray ** 2) - mu2_sq
    sigma12   = gf(ref_gray * dist_gray) - mu1_mu2

    # SSIM map
    numerator   = (2 * mu1_mu2 + C1) * (2 * sigma12 + C2)
    denominator = (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)
    ssim_map = numerator / (denominator + 1e-8)
    ssim_map = np.clip(ssim_map, -1, 1)

    # Distortion = 1 - SSIM  (0 = hoàn hảo, 2 = tệ nhất)
    distortion_map = 1.0 - ssim_map
    return distortion_map.astype(np.float32)


# ──────────────────────────────────────────────
# APPROACH 1: Saliency-weighted Pooling
# ──────────────────────────────────────────────
def approach1_saliency_pooling(ref_bgr: np.ndarray,
                                dist_bgr: np.ndarray) -> dict:
    """
    Công thức:
        W_IQM = Σ D(x,y)·S(x,y) / Σ S(x,y)

    Saliency KHÔNG ảnh hưởng đến Distortion Estimation,
    chỉ dùng làm trọng số khi Pooling.
    """
    print("[Approach 1] Tính distortion map...")
    D = compute_distortion_map(ref_bgr, dist_bgr)         # không có S

    print("[Approach 1] Tính saliency map (Spectral Residual)...")
    S = compute_saliency_SR(ref_bgr)                       # chỉ từ reference

    print("[Approach 1] Saliency-weighted pooling...")
    W_IQM = np.sum(D * S) / (np.sum(S) + 1e-8)

    # Baseline: pooling đồng đều (không có saliency) để so sánh
    baseline = np.mean(D)

    quality_score = 1.0 - W_IQM   # chuyển distortion → quality (1=tốt, 0=tệ)

    return {
        "approach": "Approach 1 — Saliency Pooling",
        "distortion_map": D,
        "saliency_map": S,
        "W_IQM_distortion": float(W_IQM),
        "quality_score": float(quality_score),
        "baseline_no_saliency": float(1.0 - baseline),
    }


# ──────────────────────────────────────────────
# APPROACH 2: Saliency modulates Distortion Estimation
# ──────────────────────────────────────────────
def approach2_saliency_distortion(ref_bgr: np.ndarray,
                                   dist_bgr: np.ndarray,
                                   threshold_alpha: float = 0.15) -> dict:
    """
    Saliency điều chỉnh ngưỡng phát hiện nhiễu loạn (detectability threshold).

    Logic:
      - threshold(x,y) = threshold_alpha * (1 - S(x,y))
        → Vùng nổi bật (S cao): ngưỡng thấp → dễ phát hiện nhiễu
        → Vùng nền   (S thấp): ngưỡng cao  → nhiễu nhỏ bị bỏ qua
      - D_adj(x,y) = max(0, D(x,y) - threshold(x,y))
      - Pooling thông thường (không dùng S làm trọng số)
    """
    print("[Approach 2] Tính saliency map (Spectral Residual)...")
    S = compute_saliency_SR(ref_bgr)

    print("[Approach 2] Tính distortion map CÓ điều chỉnh bởi saliency...")
    D_raw = compute_distortion_map(ref_bgr, dist_bgr)

    # Detectability threshold: vùng nổi bật có ngưỡng thấp hơn
    threshold_map = threshold_alpha * (1.0 - S)

    # Nhiễu dưới ngưỡng bị coi là không cảm nhận được → loại bỏ
    D_adj = np.maximum(0.0, D_raw - threshold_map)

    print("[Approach 2] Pooling thông thường (không dùng S làm trọng số)...")
    W_IQM = np.mean(D_adj)

    quality_score = 1.0 - W_IQM

    return {
        "approach": "Approach 2 — Saliency Distortion Modulation",
        "distortion_map_raw": D_raw,
        "distortion_map_adjusted": D_adj,
        "threshold_map": threshold_map,
        "saliency_map": S,
        "W_IQM_distortion": float(W_IQM),
        "quality_score": float(quality_score),
    }


# ──────────────────────────────────────────────
# VISUALIZE & SAVE RESULTS
# ──────────────────────────────────────────────
def save_visualization(ref_bgr, dist_bgr, result1, result2, output_path="result.png"):
    """Tạo ảnh tổng hợp hiển thị các map và kết quả."""
    def norm_to_uint8(arr):
        arr = arr.astype(np.float32)
        arr = (arr - arr.min()) / (arr.max() - arr.min() + 1e-8)
        return (arr * 255).astype(np.uint8)

    def colormap(gray_uint8):
        return cv2.applyColorMap(gray_uint8, cv2.COLORMAP_JET)

    H, W = ref_bgr.shape[:2]
    target_w = 200
    scale = target_w / W
    nh = int(H * scale)

    def rs(img):
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        return cv2.resize(img, (target_w, nh))

    def add_label(img, text):
        out = img.copy()
        cv2.putText(out, text, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
        cv2.putText(out, text, (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,0), 1)
        return out

    imgs_row1 = [
        add_label(rs(ref_bgr),  "Reference"),
        add_label(rs(dist_bgr), "Distorted"),
        add_label(rs(colormap(norm_to_uint8(result1["saliency_map"]))), "Saliency (SR)"),
        add_label(rs(colormap(norm_to_uint8(result1["distortion_map"]))), "Distortion Map"),
        add_label(rs(colormap(norm_to_uint8(result1["distortion_map"] * result1["saliency_map"]))), "D x S (Approach1)"),
    ]

    imgs_row2 = [
        add_label(rs(ref_bgr),  "Reference"),
        add_label(rs(dist_bgr), "Distorted"),
        add_label(rs(colormap(norm_to_uint8(result2["saliency_map"]))), "Saliency (SR)"),
        add_label(rs(colormap(norm_to_uint8(result2["distortion_map_raw"]))), "D_raw"),
        add_label(rs(colormap(norm_to_uint8(result2["distortion_map_adjusted"]))), "D_adj (Approach2)"),
    ]

    row1 = np.hstack(imgs_row1)
    row2 = np.hstack(imgs_row2)

    # Label hàng
    def row_label(row, text):
        label = np.zeros((20, row.shape[1], 3), dtype=np.uint8)
        cv2.putText(label, text, (5, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
        return np.vstack([label, row])

    row1 = row_label(row1, f"APPROACH 1 | Quality Score: {result1['quality_score']:.4f}  (baseline no-saliency: {result1['baseline_no_saliency']:.4f})")
    row2 = row_label(row2, f"APPROACH 2 | Quality Score: {result2['quality_score']:.4f}")

    separator = np.ones((6, row1.shape[1], 3), dtype=np.uint8) * 80
    final = np.vstack([row1, separator, row2])

    cv2.imwrite(output_path, final)
    print(f"\n✅ Đã lưu visualization: {output_path}")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def compute_quality(ref_path: str, dist_path: str,
                    save_vis: bool = True,
                    output_vis: str = "result_visualization.png"):
    """
    Hàm chính: nhận 2 đường dẫn ảnh, trả về quality score theo 2 approach.
    """
    ref  = cv2.imread(ref_path)
    dist = cv2.imread(dist_path)

    if ref is None:
        raise FileNotFoundError(f"Không đọc được: {ref_path}")
    if dist is None:
        raise FileNotFoundError(f"Không đọc được: {dist_path}")

    # Đảm bảo cùng kích thước
    if ref.shape != dist.shape:
        dist = cv2.resize(dist, (ref.shape[1], ref.shape[0]))
        print(f"⚠️  Resize distorted image về {ref.shape[1]}x{ref.shape[0]}")

    print("=" * 55)
    print("  SALIENCY-BASED IQM")
    print("  Visual Saliency: Spectral Residual (SR)")
    print("  Distortion base: SSIM-based local map")
    print("=" * 55)

    # ── Approach 1 ──
    print("\n── APPROACH 1: Saliency in Pooling Stage ──")
    r1 = approach1_saliency_pooling(ref, dist)
    print(f"   Quality Score : {r1['quality_score']:.4f}")
    print(f"   (Baseline w/o saliency): {r1['baseline_no_saliency']:.4f}")

    # ── Approach 2 ──
    print("\n── APPROACH 2: Saliency in Distortion Estimation ──")
    r2 = approach2_saliency_distortion(ref, dist)
    print(f"   Quality Score : {r2['quality_score']:.4f}")

    # ── Summary ──
    print("\n" + "=" * 55)
    print(f"  {'Approach':<40} {'Quality Score':>13}")
    print(f"  {'-'*53}")
    print(f"  {'Approach 1 (Saliency Pooling)':<40} {r1['quality_score']:>13.4f}")
    print(f"  {'Approach 2 (Saliency Distortion Mod.)':<40} {r2['quality_score']:>13.4f}")
    print(f"  {'Baseline (no saliency)':<40} {r1['baseline_no_saliency']:>13.4f}")
    print("=" * 55)

    if save_vis:
        save_visualization(ref, dist, r1, r2, output_path=output_vis)

    return {"approach1": r1, "approach2": r2}


# ──────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Saliency-based IQM: 2 approaches")
    parser.add_argument("reference",  help="Đường dẫn ảnh gốc (reference)")
    parser.add_argument("distorted",  help="Đường dẫn ảnh bị nhiễu (distorted)")
    parser.add_argument("--output",   default="result_visualization.png",
                        help="Đường dẫn lưu ảnh visualization (default: result_visualization.png)")
    parser.add_argument("--no-vis",   action="store_true",
                        help="Không lưu visualization")
    args = parser.parse_args()

    compute_quality(
        ref_path=args.reference,
        dist_path=args.distorted,
        save_vis=not args.no_vis,
        output_vis=args.output,
    )