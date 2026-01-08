#include "yuv_reader.h"

int read_yuv_frame(
    FILE *fp,
    x265_picture *pic,
    int width,
    int height)
{
    int y = width * height;
    int uv = y / 4;

    if (fread(pic->planes[0], 1, y, fp) != y) return 0;
    if (fread(pic->planes[1], 1, uv, fp) != uv) return 0;
    if (fread(pic->planes[2], 1, uv, fp) != uv) return 0;

    return 1;
}
