#include "roi.h"
#include <stdlib.h>

static int overlap(
    int ax1, int ay1, int ax2, int ay2,
    int bx1, int by1, int bx2, int by2)
{
    return !(ax2 <= bx1 || ax1 >= bx2 ||
             ay2 <= by1 || ay1 >= by2);
}

void apply_roi_qp(
    x265_picture *pic,
    ROI *rois,
    int num_rois,
    int ctu_size)
{
    int ctu_cols = (pic->width  + ctu_size - 1) / ctu_size;
    int ctu_rows = (pic->height + ctu_size - 1) / ctu_size;

    pic->quantOffsets =
        (float*)malloc(ctu_cols * ctu_rows * sizeof(float));

    for (int r = 0; r < ctu_rows; r++) {
        for (int c = 0; c < ctu_cols; c++) {

            int x1 = c * ctu_size;
            int y1 = r * ctu_size;
            int x2 = x1 + ctu_size;
            int y2 = y1 + ctu_size;

            float qp = +4.0f; // background

            for (int i = 0; i < num_rois; i++) {
                if (overlap(
                        x1, y1, x2, y2,
                        rois[i].x,
                        rois[i].y,
                        rois[i].x + rois[i].w,
                        rois[i].y + rois[i].h)) {
                    qp = -6.0f; // ROI
                    break;
                }
            }

            pic->quantOffsets[r * ctu_cols + c] = qp;
        }
    }
}
