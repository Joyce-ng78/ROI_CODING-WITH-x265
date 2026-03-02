# for roi in motion saliency; do
#   for qp in 22 27 32 37 42 47; do
#     python run_files/encode.py --roi_method $roi --qp $qp --openvino 0 --fullresol 0
#     # python run_files/encode.py --roi_method $roi --qp $qp --openvino 0 --fullresol 1
#     # python run_files/encode.py --roi_method $roi --qp $qp --openvino 1 --fullresol 0
#     # python run_files/encode.py --roi_method $roi --qp $qp --openvino 1 --fullresol 1
#   done
# # done
# for qp in 32 35 37 42 45 47; do
#     for preset in medium ; do
#         # python run_files/encode.py --enable_roi 0 --out output/output_rdo --out_log logs/logs_rdo --roi_method nonroi_CQP --rc 1 --qp $qp --preset $preset --rd_level 1 --rdoq_level 0
#         # python run_files/encode.py --enable_roi 0 --out output/output_rdo --out_log logs/logs_rdo --roi_method nonroi_CRF --rc 2 --qp $qp --preset $preset --rd_level 1 --rdoq_level 0
#         python run_files/encode.py --enable_roi 0 --out output/output_rdo_medium --out_log logs/logs_rdo_medium --roi_method nonroi_CRF_RDO --rc 2 --qp $qp --preset $preset --rd_level 6 --rdoq_level 2  #RDO
#         # python run_files/encode.py --enable_roi 1 --roi_method yolov5 --rc 2 --qp $qp --preset $preset
#     done
# done

# for roi in yolov5_openvino; do
#   for qp in 42 45 47; do
#     for preset in medium; do
#       python run_files/encode.py --out output/output_rdo_medium --out_log logs/logs_rdo_medium --roi_method $roi --rc 2 --qp $qp --preset $preset --rd_level 6 --rdoq_level 2
#       python run_files/encode.py --out output/output_rdo_medium --out_log logs/logs_rdo_medium --roi_method $roi --rc 2 --qp $qp --preset $preset --rd_level 5 --rdoq_level 2
#       python run_files/encode.py --out output/output_rdo_medium --out_log logs/logs_rdo_medium --roi_method $roi --rc 2 --qp $qp --preset $preset --rd_level 4 --rdoq_level 2
#       python run_files/encode.py --out output/output_rdo_medium --out_log logs/logs_rdo_medium --roi_method $roi --rc 2 --qp $qp --preset $preset --rd_level 3 --rdoq_level 2
#       python run_files/encode.py --out output/output_rdo_medium --out_log logs/logs_rdo_medium --roi_method $roi --rc 2 --qp $qp --preset $preset --rd_level 2 --rdoq_level 2
#       python run_files/encode.py --out output/output_rdo_medium --out_log logs/logs_rdo_medium --roi_method $roi --rc 2 --qp $qp --preset $preset --rd_level 1 --rdoq_level 2
#     # python run_files/encode.py --roi_method $roi --qp $qp --openvino 0 --fullresol 1
#     # python run_files/encode.py --roi_method $roi --qp $qp --openvino 1 --fullresol 0
#     # python run_files/encode.py --roi_method $roi --qp $qp --openvino 1 --fullresol 1
#     done
#   done
# done
# for qp in 32 35 37 42 45 47; do
#     for preset in medium ; do
#         # python run_files/encode.py --enable_roi 0 --out output/output_rdo --out_log logs/logs_rdo --roi_method nonroi_CQP --rc 1 --qp $qp --preset $preset --rd_level 1 --rdoq_level 0
#         # python run_files/encode.py --enable_roi 0 --out output/output_rdo --out_log logs/logs_rdo --roi_method nonroi_CRF --rc 2 --qp $qp --preset $preset --rd_level 1 --rdoq_level 0
#         python run_files/encode.py --enable_roi 0 --out output/output_rdo_medium --out_log logs/logs_rdo_medium --roi_method nonroi_CRF --rc 2 --qp $qp --preset $preset --rd_level 1 --rdoq_level 2  #RDO
#         python run_files/encode.py --enable_roi 0 --out output/output_rdo_medium --out_log logs/logs_rdo_medium --roi_method nonroi_CRF --rc 2 --qp $qp --preset $preset --rd_level 6 --rdoq_level 2  #RDO

#         # python run_files/encode.py --enable_roi 1 --roi_method yolov5 --rc 2 --qp $qp --preset $preset
#     done
# done
for qp in 37, 42; do
    for preset in medium ; do
        for rd_level in 4 5 ; do
            python src/utils/encode.py --enable_roi 1 --out output/output_rdo_medium_psy --out_log logs/logs_rdo_medium_psy --roi_method yolov5 --rc 2 --qp $qp --preset $preset --rd_level $rd_level  #RDO            python run_files/encode.py --enable_roi 1 --out output/output_rdo_medium_psy --out_log logs/logs_rdo_medium_psy --roi_method yolov5 --rc 2 --qp $qp --preset $preset --rd_level $rd_level --rdoq_level 2  #RDO
        done
    done
done