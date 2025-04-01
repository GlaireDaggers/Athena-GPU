import sys
import struct
from math import *
from PIL import Image

# table to map swizzled texel index to actual X,Y in block
block_swizzle_table = [
    (0, 0),
    (1, 0),
    (0, 1),
    (1, 1),
    (2, 0),
    (3, 0),
    (2, 1),
    (3, 1),
    (0, 2),
    (1, 2),
    (0, 3),
    (1, 3),
    (2, 2),
    (3, 2),
    (2, 3),
    (3, 3),
]

def sat(a):
    if a < 0:
        return 0
    elif a > 255:
        return 255
    else:
        return a

def decode_block_0(src_data):
    out_pixels = [[(0, 0, 0) for _ in range(4)] for _ in range(4)]
    (median_r, median_g, median_b, luma_scale, luma_idx) = struct.unpack("<BBBBI", src_data)
    luma_table = (-(luma_scale >> 1), luma_scale >> 1, luma_scale, luma_scale)
    for i in range(16):
        idx = (luma_idx >> (i * 2)) & 0b11
        offs = luma_table[idx]
        r = sat(median_r + offs)
        g = sat(median_g + offs)
        b = sat(median_b + offs)
        (px, py) = block_swizzle_table[i]
        out_pixels[px][py] = (r, g, b, 255)
    return out_pixels

print("Opening: %s" % sys.argv[1])
in_file = open(sys.argv[1], 'rb')
in_file.seek(0, 2)
in_file_len = in_file.tell()
in_file.seek(0, 0)

print("Len: %s bytes" % in_file_len)
num_blocks = in_file_len / 8
print("Num blocks: %s" % num_blocks)
blocks_size = int(sqrt(num_blocks))
print("Block dim: %s" % blocks_size)
img_size = blocks_size * 4
print("Img size: %s" % img_size)

out_img = Image.new('RGBA', (img_size, img_size))

for j in range(blocks_size):
    for i in range(blocks_size):
        bx = i * 4
        by = j * 4
        # read block
        block_data = in_file.read(8)
        block_dec = decode_block_0(block_data)
        for y in range(4):
            for x in range(4):
                c = block_dec[x][y]
                out_img.putpixel((bx + x, by + y), c)

out_img.save(sys.argv[2])
print("Finished")