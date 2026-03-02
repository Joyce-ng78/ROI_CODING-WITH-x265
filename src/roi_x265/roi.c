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

static float allocateQPOffset(
    ROI *rois,
    int num_rois,
    int width, 
    int height
) {
    int ROI_square = 0;

    for (int i = 0; i < num_rois; i++) {
        ROI_square += 
            abs(rois[i].x2 - rois[i].x1) *
            abs(rois[i].y2 - rois[i].y1);
    }

    int total_square = width * height;
    float roi_rate = (float)ROI_square / (float)total_square;

    if (roi_rate < 0.3f)
        return 1.0f;
    else if (roi_rate >= 0.3f && roi_rate < 0.7f)
        return 2.0f;
    else
        return 3.0f;
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

    // pic->quantOffsets = (float*)malloc(block_cols * block_rows * sizeof(float));
    if (pic->quantOffsets == NULL) return;
    // memset(pic->quantOffsets, 0, block_cols * block_rows * sizeof(float));
    float qpOffset = allocateQPOffset(rois, num_rois, width, height);
    for (int r = 0; r < block_rows; r++) {
        for (int c = 0; c < block_cols; c++) {

            int x1 = c * block_size;
            int y1 = r * block_size;
            int x2 = x1 + block_size;
            int y2 = y1 + block_size;

            float qp = qpOffset; // background
            for (int i = 0; i < num_rois; i++) {
                if (overlap(
                        x1, y1, x2, y2,
                        rois[i].x1,
                        rois[i].y1,
                        rois[i].x2,
                        rois[i].y2)) {
                    qp = -qpOffset; // ROI
                    break;
                }
            }

            pic->quantOffsets[r * block_cols + c] = qp;
        }
    }
}
