# ROI Coding with x265

A Region of Interest (ROI) encoder built on top of the x265 HEVC codec library. This project enables quality-differentiated video encoding by applying lower QP values (higher quality) to regions of interest while using higher QP values (lower quality) for background areas.

## Overview

This encoder reads ROI coordinates from text files and applies per-CTU (Coding Tree Unit) quantization offsets to achieve spatially varying quality in the encoded video stream. This is particularly useful for applications like video surveillance, video conferencing, and content-aware streaming where certain regions require higher quality than others.

## Features

- **ROI-based Quality Control**: Apply different quality levels to foreground (ROI) and background regions
- **Frame-by-frame ROI Support**: ROI regions can change dynamically across frames
- **Flexible QP Configuration**: Configurable base QP and ROI offsets
- **Standard HEVC Output**: Produces standard-compliant HEVC/H.265 bitstreams
- **YUV420p Input**: Supports raw YUV420 planar video input

## Prerequisites

- **x265 library**: The HEVC encoder library (libx265)
- **C compiler**: GCC or compatible C compiler
- **Make**: Build automation tool

### Installing x265

**From source:**
```bash
git clone https://bitbucket.org/multicoreware/x265_git.git
cd x265_git/build/linux
cmake ../../source
make
sudo make install
```

## Building

```bash
make
```

This will compile the encoder with all required dependencies.

## Usage

### Basic Command

```bash
./roi_x265 --input input.yuv --output output.hevc \
              --width 832 --height 480 --fps 30 --qp 27 \
              --roi-dir ./roi_data --enable-roi 1
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Input YUV420p file path | Required |
| `--output` | Output HEVC bitstream path | Required |
| `--width` | Frame width in pixels | 832 |
| `--height` | Frame height in pixels | 480 |
| `--fps` | Frame rate | 30 |
| `--qp` | Base quantization parameter (lower = higher quality) | 27 |
| `--roi-dir` | Directory containing ROI files | Required |
| `--enable-roi` | Enable/disable ROI encoding (1=on, 0=off) | 1 |
| `--print-log` | Print detailed encoding logs (1=on, 0=off) | 0 |

## ROI File Format

ROI files should be named `frame_XXXX_roi.txt` where XXXX is the zero-padded frame number (e.g., `frame_0000_roi.txt`, `frame_0001_roi.txt`).

Each ROI file contains one or more ROI regions, one per line, in the format:
```
x1, y1, x2, y2
```

Where:
- `x1, y1`: Top-left corner coordinates
- `x2, y2`: Bottom-right corner coordinates

### Example ROI File

```
100, 50, 300, 250
450, 200, 650, 400
```

This defines two ROI regions in the frame.

## Project Structure

```
.
├── main.c              # Main encoder application
├── roi.c               # ROI application logic
├── roi.h               # ROI data structures
├── roi_reader.c        # ROI file parsing
├── roi_reader.h        # ROI reader interface
├── yuv_reader.c        # YUV frame reading
├── yuv_reader.h        # YUV reader interface
├── Makefile            # Build configuration
└── README.md           # This file
```

## How It Works

1. **Frame Reading**: The encoder reads raw YUV420p frames from the input file
2. **ROI Loading**: For each frame, the corresponding ROI file is loaded from the specified directory
3. **QP Offset Application**: 
   - ROI regions receive a **-3.0 QP offset** (higher quality, more bits)
   - Background regions receive a **+3.0 QP offset** (lower quality, fewer bits)
4. **CTU-level Encoding**: The x265 encoder applies these offsets at the CTU level (default 16x16 blocks)
5. **Bitstream Output**: The encoded HEVC bitstream is written to the output file

## Encoder Configuration

The encoder uses the following x265 configuration:
- **Preset**: `veryfast` (optimized for speed)
- **Tune**: `psnr` (optimized for PSNR quality metric)
- **Rate Control**: CRF (Constant Rate Factor) mode
- **AQ Mode**: 1 (enabled with 0.0 strength)
- **CU Tree**: Enabled
- **QG Size**: 16x16 pixels

