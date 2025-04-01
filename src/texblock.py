from myhdl import *

t_State = enum("IDLE", "FILL_RGBA4444", "FILL_RGBA8888", "FILL_NXTC_0", "FILL_NXTC_1", "FILL_NXTC_2", "FILL_NXTC_3", "DEC_NXTC")

"""
=== NXTC FORMAT ===

The NXTC format is inspired by the PACKMAN compression scheme (the predecessor to ETC1) which compresses a 4x4 RGB block into 64 bits.
However, there are a few major differences:
- Instead of partitioning each 4x4 block into a pair of 2x4 strips, the entire block gets a single 24-bit median color and luma offset scale instead
- Rather than a 3-bit "luma table" value, NXTC instead supplies a full 8-bit "luma scale". Each index in the block *effectively* maps to the table (-0.5, 0.5, -1.0, 1.0) which is multiplied by the luma scale and truncated
The actual logic can be done using simple sign inversions and bit shifts, which can be trivially implemented in hardware without a lookup table
- Texel indices are stored in z-curve order, rather than in column-major order like ETC1. In other words, indices are ordered like so:
=============
| 0| 1| 4| 5|
=============
| 2| 3| 6| 7|
=============
| 8| 9|12|13|
=============
|10|11|14|15|
=============

NXTC has two modes: Mode 0 and Mode 1
Mode 0 encodes RGB data, and is assumed to be fully opaque
Mode 1 extends the width of each block to 128 bits, adding a separate "alpha block". It is encoded in exactly the same way as RGB data, but only the "red" channel is used and is interpreted as alpha channel data.
"""

# TODO: Support non-swizzled textures?

@block
def TexBlock(i_rstn, i_clk, i_blk_adr, i_blk_fmt, i_smp, o_dat, i_stb, o_ack,
             o_mem_adr, i_mem_dat, o_mem_stb, i_mem_ack, ID="texblock"):
    """
    Read-only 4x4 texture block cache

    - i_rstn: Reset signal
    - i_clk: Clock signal
    
    - i_blk_adr: Input block address
    - i_blk_fmt: Input block format (0 = rgba4444, 1 = rgba8888, 2 = nxtc mode 0, 3 = nxtc mode 1)
    - i_smp: Input index of top-left sample within 4x4 block (x + (y << 2))
    - o_dat: Output read data [4 - one per texel in 2x2 block]
    - i_stb: Request transaction signal
    - o_ack: Output data valid signal

    - o_mem_adr: Output read address to backing memory
    - i_mem_dat: Input read data from backing memory
    - o_mem_stb: Output request transaction signal to backing memory
    - i_mem_ack: Input data valid signal from backing memory
    """

    # for a single 4x4 block, cache memory is split into four banks
    # this allows a 2x2 square of texels to be read in a single clock cycle, as each texel will be retrieved from a different bank
    _cachemem = [[Signal(intbv(0)[32:]) for _ in range(4)] for _ in range(4)]

    _blkadr = Signal(intbv(0)[32:])
    _valid = Signal(bool(0))
    _state = Signal(t_State.IDLE)
    _filladr = Signal(intbv(0)[32:])
    _filloffs = Signal(intbv(0)[4:])

    _nxtc_median_rgb = Signal(intbv(0)[24:])
    _nxtc_lscale_rgb = Signal(intbv(0)[10:])
    _nxtc_offsets_rgb = [Signal(intbv(0)[10:].signed()) for _ in range(16)]

    _nxtc_median_a = Signal(intbv(0)[8:])
    _nxtc_lscale_a = Signal(intbv(0)[10:])
    _nxtc_offsets_a = [Signal(intbv(0)[10:].signed()) for _ in range(16)]

    _nxtc_mode = Signal(0)

    # final luma offset = trunc(luma_scale * scale_table[idx])
    # scale_table = (-0.5, 0.5, -1.0, 1.0)

    def sat(a):
        if a < 0:
            return intbv(0)[8:0]
        if a > 255:
            return intbv(255)[8:0]
        else:
            return intbv(a)[8:0]

    @always(i_clk.posedge, i_rstn)
    def reset_and_fill():
        if i_rstn == 0:
            _valid.next = False
            _state.next = t_State.IDLE
        elif _state == t_State.IDLE:
            # if requested block address is not loaded in cache, switch to FILL state
            if i_stb and (not _valid or _blkadr != i_blk_adr):
                print("%s Cache miss (input block address: %s, format: %s, loaded block address: %s, valid: %s)" % (ID, i_blk_adr, i_blk_fmt, _blkadr, _valid))
                if i_blk_fmt == 0:
                    _state.next = t_State.FILL_RGBA4444
                elif i_blk_fmt == 1:
                    _state.next = t_State.FILL_RGBA8888
                elif i_blk_fmt == 2:
                    _nxtc_mode.next = 0
                    _state.next = t_State.FILL_NXTC_0
                elif i_blk_fmt == 3:
                    _nxtc_mode.next = 1
                    _state.next = t_State.FILL_NXTC_0
                _filloffs.next = 0
                _filladr.next = i_blk_adr
        elif _state == t_State.FILL_RGBA4444:
            # if backing memory acks request, fill spot and increment
            # when cache is full, set block address & valid and switch back to IDLE state
            if i_mem_ack:
                bnk = concat(_filloffs[0], intbv(0)[1:])
                r0 = concat(i_mem_dat[4:0], intbv(0)[4:0])
                g0 = concat(i_mem_dat[8:4], intbv(0)[4:0])
                b0 = concat(i_mem_dat[12:8], intbv(0)[4:0])
                a0 = concat(i_mem_dat[16:12], intbv(0)[4:0])
                r1 = concat(i_mem_dat[4:0], intbv(0)[4:0])
                g1 = concat(i_mem_dat[8:4], intbv(0)[4:0])
                b1 = concat(i_mem_dat[12:8], intbv(0)[4:0])
                a1 = concat(i_mem_dat[16:12], intbv(0)[4:0])
                _cachemem[bnk][_filloffs[3:1]].next = concat(a0, b0, g0, r0)
                _cachemem[bnk + 1][_filloffs[3:1]].next = concat(a1, b1, g1, r1)
                if _filloffs == 7:
                    _blkadr.next = _filladr
                    _valid.next = True
                    _state.next = t_State.IDLE
                else:
                    _filloffs.next = _filloffs + 1
        elif _state == t_State.FILL_RGBA8888:
            # if backing memory acks request, fill spot and increment
            # when cache is full, set block address & valid and switch back to IDLE state
            if i_mem_ack:
                _cachemem[_filloffs[2:]][_filloffs[4:2]].next = i_mem_dat
                if _filloffs == 15:
                    _blkadr.next = _filladr
                    _valid.next = True
                    _state.next = t_State.IDLE
                else:
                    _filloffs.next = _filloffs + 1
        elif _state == t_State.FILL_NXTC_0:
            if i_mem_ack:
                _nxtc_median_rgb.next = i_mem_dat[24:0]
                _nxtc_lscale_rgb.next = i_mem_dat[32:24]
                _filloffs.next = 1
                _state.next = t_State.FILL_NXTC_1
        elif _state == t_State.FILL_NXTC_1:
            if i_mem_ack:
                _filloffs.next = 2
                for i in range(16):
                    low_bit = i << 1
                    high_bit = low_bit + 2
                    idx = i_mem_dat[high_bit:low_bit]
                    _nxtc_offsets_rgb[i].next = (_nxtc_lscale_rgb if idx[0] else -_nxtc_lscale_rgb) >> (0 if idx[1] else 2)
                if _nxtc_mode:
                    _state.next = t_State.FILL_NXTC_2
                else:
                    _state.next = t_State.DEC_NXTC
        elif _state == t_State.FILL_NXTC_2:
            if i_mem_ack:
                _nxtc_median_a.next = i_mem_dat[8:0]
                _nxtc_lscale_a.next = i_mem_dat[32:24]
                _filloffs.next = 3
                _state.next = t_State.FILL_NXTC_3
        elif _state == t_State.FILL_NXTC_3:
            if i_mem_ack:
                for i in range(16):
                    low_bit = i << 1
                    high_bit = low_bit + 2
                    idx = i_mem_dat[high_bit:low_bit]
                    _nxtc_offsets_a[i].next = (_nxtc_lscale_a if idx[0] else -_nxtc_lscale_a) >> (0 if idx[1] else 1)
                _state.next = t_State.DEC_NXTC
        elif _state == t_State.DEC_NXTC:
            for i in range(16):
                offs_rgb = _nxtc_offsets_rgb[i]
                offs_a = _nxtc_offsets_a[i]
                r = sat(_nxtc_median_rgb[8:0] + offs_rgb)
                g = sat(_nxtc_median_rgb[16:8] + offs_rgb)
                b = sat(_nxtc_median_rgb[24:16] + offs_rgb)
                a = sat(_nxtc_median_a + offs_a) if _nxtc_mode else intbv(255)[8:0]
                col = concat(a, b, g, r)
                bnk = i & 3
                bnkoffs = i >> 2
                _cachemem[bnk][bnkoffs].next = col
            _blkadr.next = _filladr
            _valid.next = True
            _state.next = t_State.IDLE

    @always_comb
    def access():
        o_ack.next = _blkadr == i_blk_adr and _valid and i_stb

        sy = i_smp[4:2]
        sx = i_smp[2:0]
        smp0 = concat(sy,                   sx)
        smp1 = concat(sy,                   intbv(sx + 1)[2:])
        smp2 = concat(intbv(sy + 1)[2:],    sx)
        smp3 = concat(intbv(sy + 1)[2:],    intbv(sx + 1)[2:])

        bnk0 = concat(smp0[2], smp0[0])

        adr0 = concat(smp0[3], smp0[1])
        adr1 = concat(smp1[3], smp1[1])
        adr2 = concat(smp2[3], smp2[1])
        adr3 = concat(smp3[3], smp3[1])

        if bnk0 == 0:
            o_dat[0].next = _cachemem[0][adr0]
            o_dat[1].next = _cachemem[1][adr1]
            o_dat[2].next = _cachemem[2][adr2]
            o_dat[3].next = _cachemem[3][adr3]
        elif bnk0 == 1:
            o_dat[0].next = _cachemem[1][adr0]
            o_dat[1].next = _cachemem[0][adr1]
            o_dat[2].next = _cachemem[3][adr2]
            o_dat[3].next = _cachemem[2][adr3]
        elif bnk0 == 2:
            o_dat[0].next = _cachemem[2][adr0]
            o_dat[1].next = _cachemem[3][adr1]
            o_dat[2].next = _cachemem[0][adr2]
            o_dat[3].next = _cachemem[1][adr3]
        elif bnk0 == 3:
            o_dat[0].next = _cachemem[3][adr0]
            o_dat[1].next = _cachemem[2][adr1]
            o_dat[2].next = _cachemem[1][adr2]
            o_dat[3].next = _cachemem[0][adr3]

        o_mem_adr.next = _filladr + _filloffs
        o_mem_stb.next = (_state == t_State.FILL_RGBA4444 or _state == t_State.FILL_RGBA8888 or _state == t_State.FILL_NXTC_0 or _state == t_State.FILL_NXTC_1 or _state == t_State.FILL_NXTC_2 or _state == t_State.FILL_NXTC_3)

    return reset_and_fill, access