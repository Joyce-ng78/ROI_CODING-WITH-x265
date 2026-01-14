./roi_x265 --input input_yuv/BasketballDrive_1920x1080_15.yuv \
--output output/out_nonroi.hevc   \
--width 1920 --height 1080   \
--fps 15 --qp 42 --roi-dir roi \
--enable-roi 0 --print-log 1 >logs/encode_nonroi.txt 2>&1 \
&&
./TAppDecoderStatic -b output/out_nonroi.hevc -o output/out_nonroi.yuv >logs/nonroi.txt 2>&1
