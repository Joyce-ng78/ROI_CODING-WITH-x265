#ifndef ROI_H
#define ROI_H

#include <x265.h>

typedef struct {
    int x1;
    int y1;
    int x2;
    int y2;
} ROI;

void apply_roi_qp(
    x265_picture *pic,
    ROI *rois,
    int num_rois,
    int ctu_size
);

#endif
