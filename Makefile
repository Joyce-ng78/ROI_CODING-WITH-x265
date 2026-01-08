CC = gcc
CFLAGS = -O2 -I/usr/local/include
LDFLAGS = -L/usr/local/lib -lx265

SRC = src/main.c src/roi.c src/roi_reader.c src/yuv_reader.c
OBJ = $(SRC:.c=.o)

all: roi_x265

roi_x265: $(OBJ)
	$(CC) -o $@ $(OBJ) $(LDFLAGS)

clean:
	rm -f $(OBJ) roi_x265
