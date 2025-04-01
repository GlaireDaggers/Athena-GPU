import sys
import struct
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

def encode_block_0(b: Image.Image):
    # calculate median rgb & luma, store luma per pixel
    median_r = 0
    median_g = 0
    median_b = 0
    lumas = [0 for _ in range(16)]
    for i in range(16):
        px_pos = block_swizzle_table[i]
        px_rgb = b.getpixel(px_pos)
        px_luma = max(px_rgb[0], px_rgb[1], px_rgb[2])
        lumas[i] = px_luma
        median_r += px_rgb[0]
        median_g += px_rgb[1]
        median_b += px_rgb[2]
    median_r >>= 4
    median_g >>= 4
    median_b >>= 4
    median_luma = max(median_r, median_g, median_b)
    # calculate luma offset from median per pixel & offset range
    luma_offs = [0 for _ in range(16)]
    luma_scale = 0
    for i in range(16):
        luma_offs[i] = lumas[i] - median_luma
        offs_abs = abs(luma_offs[i])
        if offs_abs > luma_scale:
            luma_scale = offs_abs
    luma_table = (-(luma_scale >> 1), luma_scale >> 1, luma_scale, luma_scale)
    # convert luma offsets to indices into table (-0.25, 0.25, -1.0, 1.0) and pack into 32 bits
    luma_bits = 0
    if luma_scale > 0:
        for i in range(16):
            # search for luma offset which minimizes error
            l = [sat(median_luma + luma_table[j]) for j in range(4)]
            e = [abs(lumas[i] - l[j]) for j in range(4)]
            luma_idx = e.index(min(e))
            luma_bits |= luma_idx << (i * 2)
    # return packed 64-bit result
    return struct.pack("<BBBBI", median_r, median_g, median_b, luma_scale, luma_bits)

img = Image.open(sys.argv[1]).convert("RGBA")
out_file = open(sys.argv[2], 'wb')

blocks_wide = img.width >> 2
blocks_high = img.height >> 2

for j in range(blocks_wide):
    for i in range(blocks_high):
        bx = i * 4
        by = j * 4
        block_src = img.crop((bx, by, bx + 4, by + 4))
        block_enc = encode_block_0(block_src)
        out_file.write(block_enc)

out_file.close()
print("Finished")