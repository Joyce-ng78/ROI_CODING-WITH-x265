./roi_x265 --input input_yuv/BasketballDrive_1920x1080_15.yuv \
--output output/out_roi_27.hevc   \
--width 1920 --height 1080   \
--fps 15 --qp 27 --roi-dir roi \
--enable-roi 1 --print-log 1 >logs/encode_roi_27.txt 2>&1 \
&&
./TAppDecoderStatic -b output/out_roi_27.hevc \
-o output/out_roi_27.yuv >logs/decode_roi_27.txt 2>&1 \