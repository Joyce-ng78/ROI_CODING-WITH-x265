#include <x265.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "roi.h"
#include "roi_reader.h"
#include "yuv_reader.h"

#define MAX_ROI 50
/* ---------------- CLI helpers ---------------- */

static const char* get_arg(int argc, char **argv, const char *key)
{
    for (int i = 1; i < argc - 1; i++) {
        if (!strcmp(argv[i], key))
            return argv[i + 1];
    }
    return NULL;
}

static int get_arg_int(int argc, char **argv, const char *key, int def)
{
    const char *v = get_arg(argc, argv, key);
    return v ? atoi(v) : def;
}

static void print_usage(const char *prog)
{
    printf(
        "Usage:\n"
        "  %s --input in.yuv --output out.hevc \\\n"
        "     --width W --height H --fps FPS --qp QP --roi-dir DIR\n\n"
        "Options:\n"
        "  --input     input YUV420p file\n"
        "  --output    output HEVC bitstream\n"
        "  --width     frame width\n"
        "  --height    frame height\n"
        "  --fps       frame rate (default: 30)\n"
        "  --qp        base QP (default: 28)\n"
        "  --roi-dir   ROI directory (frame_XXXX.txt)\n",
        prog
    );
}

int main(int argc, char **argv)
{
    const char *input  = get_arg(argc, argv, "--input");
    const char *output = get_arg(argc, argv, "--output");
    const char *roi_dir = get_arg(argc, argv, "--roi-dir");

    if (!input || !output || !roi_dir) {
        print_usage(argv[0]);
        return -1;
    }

    int width  = get_arg_int(argc, argv, "--width",  832);
    int height = get_arg_int(argc, argv, "--height", 480);
    int fps    = get_arg_int(argc, argv, "--fps",    30);
    int qp     = get_arg_int(argc, argv, "--qp",     27);

    FILE *fyuv = fopen(input, "rb");
    FILE *fout = fopen(output, "wb");
    if (!fyuv || !fout) {
        fprintf(stderr, "Cannot open input/output file\n");
        return -1;
    }

    /* ---------------- x265 params ---------------- */

    x265_param *param = x265_param_alloc();
    x265_param_default(param);

    param->sourceWidth  = width;
    param->sourceHeight = height;
    param->fpsNum   = fps;
    param->fpsDenom = 1;

    param->rc.rateControlMode = X265_RC_CQP;
    param->rc.qp = qp;
    
    /* ---------------- intra mode ---------------- */
    param->bframes = 0;
    param->lookaheadDepth = 0;
    // param->keyframeMax = 1;
    // param->keyframeMin = 0;
    // param->scenecutThreshold = 0;  // optional nhưng nên có
    // param->bIntraRefresh = 0;
    // param->bOpenGOP = 0;
    // param->bRepeatHeaders = 1;

    

    // param->maxNumReferences = 0;
    // param->frameNumThreads = 1;
    

    /* ---------------- write header ---------------- */

    param->bAnnexB = 1;
    param->logLevel = X265_LOG_DEBUG;
    /* ---------------- x265 encoder ---------------- */
    x265_encoder *encoder = x265_encoder_open(param);
    if (!encoder) {
        fprintf(stderr, "x265_encoder_open failed\n");
        return -1;
    }

    /* ---------------- write headers ---------------- */

    x265_nal *nals;
    uint32_t num_nals;

    x265_encoder_headers(encoder, &nals, &num_nals);
    for (uint32_t i = 0; i < num_nals; i++) {
        fwrite(nals[i].payload, 1, nals[i].sizeBytes, fout);
    }

    /* ---------------- picture ---------------- */

    x265_picture pic, pic_out;
    x265_picture_init(param, &pic);
    x265_picture_init(param, &pic_out);

    pic.width  = width;
    pic.height = height;
    pic.stride[0] = width;
    pic.stride[1] = width / 2;
    pic.stride[2] = width / 2;

    pic.planes[0] = malloc(width * height);
    pic.planes[1] = malloc(width * height / 4);
    pic.planes[2] = malloc(width * height / 4);

    /* ---------------- encode loop ---------------- */
    int frame = 0;
    while (read_yuv_frame(fyuv, &pic, width, height)) {

        ROI rois[MAX_ROI];
        char roi_file[256];
        snprintf(roi_file, sizeof(roi_file),
                 "%s/frame_%04d_roi.txt", roi_dir, frame);
        int num_rois = load_roi_txt(roi_file, rois);

        apply_roi_qp(
            &pic,
            rois,
            num_rois,
            param->maxCUSize
        );

        int ctu_size = param->maxCUSize;
        int ctu_cols = (width  + ctu_size - 1) / ctu_size;
        int ctu_rows = (height + ctu_size - 1) / ctu_size;

        printf("Frame %d: QP offset map (%dx%d CTUs with CTU_size %d)\n",
            frame, ctu_rows, ctu_cols, ctu_size);
        int base_qp = param->rc.qp;

        for (int r = 0; r < ctu_rows; r++) {
            for (int c = 0; c < ctu_cols; c++) {
                int idx = r * ctu_cols + c;
                float qpo = pic.quantOffsets ? pic.quantOffsets[idx] : 0.0;
                printf("%6.1f ", qpo);
            }
            printf("\n");
        }
        printf("\n");

        x265_nal *nals;
        uint32_t num_nals;

        x265_encoder_encode(
            encoder,
            &nals,
            &num_nals,
            &pic,
            &pic_out
        );

        for (uint32_t i = 0; i < num_nals; i++) {
            fwrite(nals[i].payload, 1, nals[i].sizeBytes, fout);
        }
        // if (num_nals > 0) {
        //     for (uint32_t i = 0; i < num_nals; i++)
        //         fwrite(nals[i].payload, 1, nals[i].sizeBytes, fout);
        // }

        if (pic.quantOffsets) {
            free(pic.quantOffsets);
            pic.quantOffsets = NULL;
        }

        frame++;
    }
    
    /* ---------------- flush ---------------- */

    while (x265_encoder_encode(encoder, &nals, &num_nals, NULL, &pic_out)) {
        for (uint32_t i = 0; i < num_nals; i++) {
            fwrite(nals[i].payload, 1, nals[i].sizeBytes, fout);
        }
    }
    
    /* ---------------- cleanup ---------------- */

    free(pic.planes[0]);
    free(pic.planes[1]);
    free(pic.planes[2]);

    x265_encoder_close(encoder);
    x265_param_free(param);
    fclose(fyuv);
    fclose(fout);
    return 0;
}
