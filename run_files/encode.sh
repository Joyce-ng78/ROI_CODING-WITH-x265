for roi in yolov5; do
  for qp in  22 27 32 37 42 47; do
    for preset in ultrafast superfast veryfast faster fast medium slow slower; do
      python run_files/encode.py --roi_method $roi --qp $qp --preset $preset
    # python run_files/encode.py --roi_method $roi --qp $qp --openvino 0 --fullresol 1
    # python run_files/encode.py --roi_method $roi --qp $qp --openvino 1 --fullresol 0
    # python run_files/encode.py --roi_method $roi --qp $qp --openvino 1 --fullresol 1
    done
  done
done