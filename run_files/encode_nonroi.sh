./roi_x265 --input input_yuv/BasketballDrive_1920x1080_15.yuv \
--output output/out_nonroi_27.hevc   \
--width 1920 --height 1080   \
--fps 15 --qp 27 --roi-dir roi \
--enable-roi 0 --print-log 1 >logs/encode_nonroi_27.txt 2>&1 \
&&
./TAppDecoderStatic -b output/out_nonroi_27.hevc \
-o output/out_nonroi_27.yuv >logs/decode_nonroi_27.txt 2>&1