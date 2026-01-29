# ./roi_x265 --input input_yuv/BasketballDrive_1920x1080_15.yuv \
# --output output/out_nonroi_27.hevc   \
# --width 1920 --height 1080   \
# --fps 15 --qp 27 --roi-dir roi \
# --enable-roi 0 --print-log 1 >logs/encode_nonroi_27.txt 2>&1 \
# &&
# ./TAppDecoderStatic -b output/out_nonroi_27.hevc \
# -o output/out_nonroi_27.yuv > logs/decode_nonroi_27.txt 2>&1

python run_files/encode.py --roi_method nonroi --qp 22 --enable_roi 0
python run_files/encode.py --roi_method nonroi --qp 27 --enable_roi 0
python run_files/encode.py --roi_method nonroi --qp 32 --enable_roi 0
python run_files/encode.py --roi_method nonroi --qp 37 --enable_roi 0
python run_files/encode.py --roi_method nonroi --qp 42 --enable_roi 0
python run_files/encode.py --roi_method nonroi --qp 47 --enable_roi 0
