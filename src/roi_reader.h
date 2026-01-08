#ifndef ROI_READER_H
#define ROI_READER_H

#include "roi.h"

int load_roi_txt(
    const char *filename,
    ROI *rois,
    int max_roi
);

#endif
