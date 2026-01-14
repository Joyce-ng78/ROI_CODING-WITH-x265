#include "roi.h"
#include <stdlib.h>
#include <string.h>

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
    int block_size)
{
    int width  = pic->width;
    int height = pic->height;

    int block_cols = (width  + block_size - 1) / block_size;
    int block_rows = (height + block_size - 1) / block_size;

    pic->quantOffsets = (float*)malloc(block_cols * block_rows * sizeof(float));
    memset(pic->quantOffsets, 0, block_cols * block_rows * sizeof(float));
    for (int r = 0; r < block_rows; r++) {
        for (int c = 0; c < block_cols; c++) {

            int x1 = c * block_size;
            int y1 = r * block_size;
            int x2 = x1 + block_size;
            int y2 = y1 + block_size;

            float qp = +3.0f; // background
            for (int i = 0; i < num_rois; i++) {
                if (overlap(
                        x1, y1, x2, y2,
                        rois[i].x1,
                        rois[i].y1,
                        rois[i].x2,
                        rois[i].y2)) {
                    qp = -3.0f; // ROI
                    break;
                }
            }

            pic->quantOffsets[r * block_cols + c] = qp;
        }
    }
}
