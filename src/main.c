#include <x265.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "roi.h"
#include "roi_reader.h"
#include "yuv_reader.h"

#define MAX_ROI 50
/* ---------------- CLI helpers ---------------- */

static const char *get_arg(int argc, char **argv, const char *key)
{
    for (int i = 1; i < argc - 1; i++)
    {
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

static int get_arg_bool(int argc, char **argv, const char *key, int def)
{
    const char *v = get_arg(argc, argv, key);
    if (!v)
        return def;
    return atoi(v) != 0;
}

static void print_usage(const char *prog)
{
    printf(
        "Usage:\n"
        "  %s --input in.yuv --output out.hevc \\\n"
        "     --width W --height H --fps FPS --qp QP --roi-dir DIR \\\n"
        "     --enable-roi 1  --print-log 0\n\n"
        "Options:\n"
        "  --input     input YUV420p file\n"
        "  --output    output HEVC bitstream\n"
        "  --width     frame width\n"
        "  --height    frame height\n"
        "  --fps       frame rate (default: 30)\n"
        "  --qp        base QP (default: 28)\n"
        "  --roi-dir   ROI directory (frame_XXXX.txt)\n"
        "  --enable-roi  apply ROI (1=on, 0=off, default: 1)\n"
        "  --print-log      print log (1=on, 0=off, default: 0) \n",
        prog);
}

int main(int argc, char **argv)
{
    const char *input = get_arg(argc, argv, "--input");
    const char *output = get_arg(argc, argv, "--output");
    const char *roi_dir = get_arg(argc, argv, "--roi-dir");

    if (!input || !output || !roi_dir)
    {
        print_usage(argv[0]);
        return -1;
    }

    int width = get_arg_int(argc, argv, "--width", 832);
    int height = get_arg_int(argc, argv, "--height", 480);
    int fps = get_arg_int(argc, argv, "--fps", 30);
    int qp = get_arg_int(argc, argv, "--qp", 27);
    int enable_roi = get_arg_bool(argc, argv, "--enable-roi", 1);
    int print_log = get_arg_bool(argc, argv, "--print-log", 0);
    printf("qp %d\n", qp);
    printf("enable roi: %d\n", enable_roi);
    FILE *fyuv = fopen(input, "rb");
    FILE *fout = fopen(output, "wb");
    if (!fyuv || !fout)
    {
        fprintf(stderr, "Cannot open input/output file\n");
        return -1;
    }

    /* ---------------- x265 params ---------------- */

    x265_param *param = x265_param_alloc();
    x265_param_default_preset(param, "veryfast", "psnr");

    param->sourceWidth = width;
    param->sourceHeight = height;
    param->fpsNum = fps;
    param->fpsDenom = 1;

    param->rc.rateControlMode = X265_RC_CRF;
    // param->rc.qp = qp;'=
    // param->rc.rateControlMode = X265_RC_CQP;
    param->rc.qp = qp;
    param->rc.rfConstant= (double)qp;

    param->rc.aqMode = 1;
    param->rc.aqStrength = 0.0f;
    param->rc.qgSize = 16;
    param->rc.cuTree = 1;
    // x265_param_default(param);

    // strncpy(param->analysisLoad, "analysis.dat", X265_MAX_STRING_SIZE);
    // param->analysisLoad[X265_MAX_STRING_SIZE-1] = '\0';  // đảm bảo null-terminated

    // strncpy(param->analysisSave, "analysis.dat", X265_MAX_STRING_SIZE);
    // param->analysisSave[X265_MAX_STRING_SIZE-1] = '\0';
    // param->analysisLoadReuseLevel = 1;  // sử dụng dữ liệu phân tích đã lưu
    /* ---------------- intra mode ---------------- */
    // param->bframes = 0;
    // param->lookaheadDepth = 1;
    // param->lookaheadSlices = 1;

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
    param->logLevel = X265_LOG_FULL;
    // printf("===== x265 params =====\n");
    // printf("Resolution      : %dx%d\n", param->sourceWidth, param->sourceHeight);
    // printf("FPS             : %d/%d\n", param->fpsNum, param->fpsDenom);

    // printf("RC mode         : %d (CQP=%d)\n",
    //     param->rc.rateControlMode, X265_RC_CQP);
    // printf("QP              : %d\n", param->rc.qp);

    // printf("AQ mode         : %d\n", param->rc.aqMode);
    // printf("AQ strength     : %.2f\n", param->rc.aqStrength);
    // printf("CU Tree         : %d\n", param->rc.cuTree);
    // printf("QG size         : %d\n", param->rc.qgSize);

    // printf("B-frames        : %d\n", param->bframes);
    // printf("Lookahead depth : %d\n", param->lookaheadDepth);

    // printf("AnnexB          : %d\n", param->bAnnexB);
    // printf("Log level       : %d\n", param->logLevel);
    // printf("========================\n");

    /* ---------------- analysis ---------------- */
    // x265_analysis_data analysis;
    // // x265_analysis_data_init(&analysis);
    // x265_alloc_analysis_data(param, &analysis);

    /* ---------------- x265 encoder ---------------- */
    x265_encoder *encoder = x265_encoder_open(param);
    if (!encoder)
    {
        fprintf(stderr, "x265_encoder_open failed\n");
        return -1;
    }

    /* ---------------- write headers ---------------- */

    x265_nal *nals;
    uint32_t num_nals;

    x265_encoder_headers(encoder, &nals, &num_nals);
    for (uint32_t i = 0; i < num_nals; i++)
    {
        fwrite(nals[i].payload, 1, nals[i].sizeBytes, fout);
    }

    /* ---------------- picture ---------------- */

    x265_picture pic, pic_out;
    x265_picture_init(param, &pic);
    x265_picture_init(param, &pic_out);
    // pic.analysisData = analysis;
    pic.width = width;
    pic.height = height;
    pic.stride[0] = width;
    pic.stride[1] = width / 2;
    pic.stride[2] = width / 2;

    pic.planes[0] = malloc(width * height);
    pic.planes[1] = malloc(width * height / 4);
    pic.planes[2] = malloc(width * height / 4);

    /* ---------------- encode loop ---------------- */
    int frame = 0;
    while (read_yuv_frame(fyuv, &pic, width, height))
    {
        // printf("params rc.aqMode=%d rc.aqStrength=%f rc.qgSize=%d\n", param->rc.aqMode, param->rc.aqStrength, param->rc.qgSize);

        pic.pts = (int64_t)frame;
        pic.quantOffsets = NULL;
        if (enable_roi)
        {
            ROI rois[MAX_ROI];
            char roi_file[256];

            snprintf(roi_file, sizeof(roi_file),
                     "%s/frame_%04d_roi.txt", roi_dir, frame);

            int num_rois = load_roi_txt(roi_file, rois);
            if (num_rois > 0)
            {
                apply_roi_qp(
                    &pic,
                    rois,
                    num_rois,
                    param->rc.qgSize);
            }
            // Debug Log
            if (pic.quantOffsets && print_log)
            {
                printf("Frame %d: Sending %d roi with quantOffsets to encoder...\n", frame, num_rois);
                // (Giữ nguyên đoạn code print map của bạn ở đây nếu muốn)
            }
        }

        if (enable_roi && pic.quantOffsets && print_log)
        {
            int qgSize = param->maxCUSize; // Dùng 16 thay vì maxCUSize
            int qg_cols = (width + qgSize - 1) / qgSize;
            int qg_rows = (height + qgSize - 1) / qgSize;

            printf("Frame %d: QP offset map (%dx%d Blocks of 16x16)\n", frame, qg_rows, qg_cols);

            // for (int r = 0; r < qg_rows; r++) {
            //     for (int c = 0; c < qg_cols; c++) {
            //         int idx = r * qg_cols + c;
            //         // Lưu ý: Giá trị âm = Giảm QP (Nét hơn), Dương = Tăng QP (Mờ hơn)
            //         printf("%4.1f ", pic.quantOffsets[idx]);
            //     }
            //     printf("\n");
            // }
            printf("\n");
        }

        // x265_alloc_analysis_data(param, &analysis);
        printf("aqmode %d pic quantOffsets", param->rc.aqMode);

        x265_nal *nals;
        uint32_t num_nals;

        x265_encoder_encode(
            encoder,
            &nals,
            &num_nals,
            &pic,
            &pic_out);

        for (uint32_t i = 0; i < num_nals; i++)
        {
            fwrite(nals[i].payload, 1, nals[i].sizeBytes, fout);
        }
        // if (num_nals > 0) {
        //     for (uint32_t i = 0; i < num_nals; i++)
        //         fwrite(nals[i].payload, 1, nals[i].sizeBytes, fout);
        // }

        if (pic.quantOffsets)
        {
            free(pic.quantOffsets);
            pic.quantOffsets = NULL;
        }

        frame++;
    }

    /* ---------------- flush ---------------- */

    while (x265_encoder_encode(encoder, &nals, &num_nals, NULL, &pic_out))
    {
        for (uint32_t i = 0; i < num_nals; i++)
        {
            fwrite(nals[i].payload, 1, nals[i].sizeBytes, fout);
        }
    }

    /* ---------------- cleanup ---------------- */

    // free(pic.planes[0]);
    // free(pic.planes[1]);
    // free(pic.planes[2]);

    x265_encoder_close(encoder);
    x265_param_free(param);
    // x265_picture_free(&pic);
    // x265_picture_free(&pic_out);
    // free(nals);
    fclose(fyuv);
    fclose(fout);
    return 0;
}
