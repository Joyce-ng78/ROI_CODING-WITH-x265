#include "roi_reader.h"
#include <stdio.h>

int load_roi_txt(
    const char *filename,
    ROI *rois
    )
{
    FILE *f = fopen(filename, "r");
    if (!f) {
        printf("No ROI file found: %s\n", filename);
        return 0;
    } 

    int n = 0;
    while (fscanf(f, " %d%*[, ]%d%*[, ]%d%*[, ]%d",
                  &rois[n].x1,
                  &rois[n].y1,
                  &rois[n].x2,
                  &rois[n].y2) == 4) {
        n++;
    };
    fclose(f);
    return n;
}