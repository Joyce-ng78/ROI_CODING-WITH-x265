# for roi in motion saliency; do
#   for qp in 22 27 32 37 42 47; do
#     python run_files/encode.py --roi_method $roi --qp $qp --openvino 0 --fullresol 0
#     # python run_files/encode.py --roi_method $roi --qp $qp --openvino 0 --fullresol 1
#     # python run_files/encode.py --roi_method $roi --qp $qp --openvino 1 --fullresol 0
#     # python run_files/encode.py --roi_method $roi --qp $qp --openvino 1 --fullresol 1
#   done
# done
for qp in  22 27 32 37 42 47; do
    for preset in ultrafast superfast veryfast faster fast medium slow slower; do
        python run_files/encode.py --enable_roi 0 --roi_method nonroi_CQP --rc 1 --qp $qp --preset $preset
        python run_files/encode.py --enable_roi 0 --roi_method nonroi_CRF --rc 2 --qp $qp --preset $preset
        # python run_files/encode.py --enable_roi 1 --roi_method yolov5 --rc 2 --qp $qp --preset $preset
    done
done
