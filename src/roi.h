#ifndef ROI_H
#define ROI_H

#include <x265.h>

typedef struct {
    int x;
    int y;
    int w;
    int h;
} ROI;

void apply_roi_qp(
    x265_picture *pic,
    ROI *rois,
    int num_rois,
    int ctu_size
);

#endif
