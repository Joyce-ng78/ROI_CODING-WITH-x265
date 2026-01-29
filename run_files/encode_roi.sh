# ./roi_x265 --input input_yuv/BasketballDrive_1920x1080_15.yuv \
# --output output/out_roi_27.hevc   \
# --width 1920 --height 1080   \
# --fps 15 --qp 27 --roi-dir roi \
# --enable-roi 1 --print-log 1 >logs/encode_roi_27.txt 2>&1 \
# &&
# ./TAppDecoderStatic -b output/out_roi_27.hevc \
# -o output/out_roi_27.yuv >logs/decode_roi_27.txt 2>&1 \

# ./roi_x265 --input input_yuv/class_B/BasketballDrive_1920x1080_100.yuv \
# --output temp/cqp.hevc   \
# --width 1920 --height 1080 --rc 1  \
# --fps 15 --qp 27 --roi-dir roi/yolov5/BasketballDrive_1920x1080_100 \
# --enable-roi 1 --print-log 0 >temp/cqp.txt 2>&1 \
# &&
# ./TAppDecoderStatic -b temp/cqp.hevc \
# -o temp/temp.yuv >temp/cqp_dec.txt 2>&1 \
# &&
./roi_x265 --input input_yuv/class_B/BasketballDrive_1920x1080_100.yuv \
--output temp/cqp.hevc  --preset slow \
--width 1920 --height 1080 --rc 2  \
--fps 15 --qp 27 --roi-dir roi/yolov5/BasketballDrive_1920x1080_100 \
--enable-roi 1 --print-log 0 >temp/crf_slow.txt 2>&1 \
&&
./TAppDecoderStatic -b temp/cqp.hevc \
-o temp/temp.yuv >temp/crf_dec_slow.txt 2>&1 