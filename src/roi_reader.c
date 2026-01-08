#include "roi_reader.h"
#include <stdio.h>

int load_roi_txt(
    const char *filename,
    ROI *rois,
    int max_roi)
{
    FILE *f = fopen(filename, "r");
    if (!f) return 0;

    int n = 0;
    while (n < max_roi &&
           fscanf(f, "%d %d %d %d",
                  &rois[n].x,
                  &rois[n].y,
                  &rois[n].w,
                  &rois[n].h) == 4) {
        n++;
    }

    fclose(f);
    return n;
}
