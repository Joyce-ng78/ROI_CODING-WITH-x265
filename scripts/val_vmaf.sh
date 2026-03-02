#!/bin/bash

# ==============================
# CONFIG
# ==============================
FFMPEG=./ffmpeg
WIDTH=1920
HEIGHT=1080
PIX_FMT=yuv420p

REF_DIR="./input_yuv/class_B"
DIST_ROOT="./output_RCF"
OUT_ROOT="./vmaf_results"

QPS=(22 27 32 37 42 47)

# ==============================
# CHECK
# ==============================
if [ ! -f "$FFMPEG" ]; then
  echo "[ERROR] FFmpeg not found: $FFMPEG"
  exit 1
fi

mkdir -p "$OUT_ROOT"

# ==============================
# RUN VMAF (RESUME SAFE)
# ==============================
for REF_YUV in "$REF_DIR"/*.yuv; do
  BASENAME=$(basename "$REF_YUV")
  SEQ_NAME=${BASENAME%%_*}

  echo "======================================"
  echo "▶ Sequence: $SEQ_NAME"
  echo "======================================"

  for METHOD_DIR in "$DIST_ROOT"/*; do
    METHOD=$(basename "$METHOD_DIR")
    SEQ_OUT_DIR="$OUT_ROOT/$METHOD/$SEQ_NAME"
    mkdir -p "$SEQ_OUT_DIR"

    echo "  ▶ Method: $METHOD"

    for QP in "${QPS[@]}"; do
      DIST_YUV="$METHOD_DIR/qp${QP}/$BASENAME"
      OUT_JSON="$SEQ_OUT_DIR/vmaf_qp${QP}.json"

      # ---- CHECK DONE ----
      if [ -s "$OUT_JSON" ]; then
        echo "    [SKIP] QP${QP} already done"
        continue
      fi

      if [ ! -f "$DIST_YUV" ]; then
        echo "    [MISS] QP${QP} YUV not found"
        continue
      fi

      echo "    ▶ Running QP${QP}"

      "$FFMPEG" \
        -s ${WIDTH}x${HEIGHT} -pix_fmt $PIX_FMT -i "$DIST_YUV" \
        -s ${WIDTH}x${HEIGHT} -pix_fmt $PIX_FMT -i "$REF_YUV" \
        -lavfi libvmaf=log_fmt=json:log_path="$OUT_JSON" \
        -f null -

      # ---- VERIFY RESULT ----
      if [ -s "$OUT_JSON" ]; then
        echo "    ✔ Done QP${QP}"
      else
        echo "    ✖ Failed QP${QP}, will retry next run"
        rm -f "$OUT_JSON"
      fi
    done
  done
done

echo "======================================"
echo "ALL VMAF FINISHED (or resumable)"
echo "Results in $OUT_ROOT/"
