#ifndef YUV_READER_H
#define YUV_READER_H

#include <x265.h>
#include <stdio.h>

int read_yuv_frame(
    FILE *fp,
    x265_picture *pic,
    int width,
    int height
);

#endif
