#include <x265.h>
#include <stdio.h>
#include <stdlib.h>
#include "roi.h"
#include "roi_reader.h"
#include "yuv_reader.h"

#define MAX_ROI 50

int main(int argc, char **argv)
{
    int width = 832;
    int height = 480;

    FILE *fyuv = fopen("input_yuv/BasketballDrill_832x480_15.yuv", "rb");
    FILE *fout = fopen("out.hevc", "wb");

    x265_param *param = x265_param_alloc();
    x265_param_default(param);

    param->sourceWidth  = width;
    param->sourceHeight = height;
    param->rc.rateControlMode = X265_RC_CRF;
    param->fpsNum=15;
    param->fpsDenom=1;
    //param->rc.qpOffsets = 1;
    param->lookaheadDepth = 0;
    param->bframes = 0;

    x265_encoder *encoder = x265_encoder_open(param);

    x265_picture pic;
    x265_picture pic_out;
    x265_picture_init(param, &pic);

    pic.planes[0] = malloc(width * height);
    pic.planes[1] = malloc(width * height / 4);
    pic.planes[2] = malloc(width * height / 4);

    int frame = 0;
    while (read_yuv_frame(fyuv, &pic, width, height)) {

        ROI rois[MAX_ROI];
        char roi_file[256];
        sprintf(roi_file, "roi/frame_%04d.txt", frame);

        int num_rois = load_roi_txt(roi_file, rois);

        apply_roi_qp(
            &pic,
            rois,
            num_rois,
            param->maxCUSize
        );

        x265_nal *nals;
        uint32_t num_nals;

        x265_encoder_encode(
            encoder,
            &nals,
            &num_nals,
            &pic,
            &pic_out
        );

        for (uint32_t i = 0; i < num_nals; i++)
            fwrite(nals[i].payload, 1,
                   nals[i].sizeBytes, fout);

        free(pic.quantOffsets);
        pic.quantOffsets = NULL;

        frame++;
    }

    x265_encoder_close(encoder);
    x265_param_free(param);

    return 0;
}
