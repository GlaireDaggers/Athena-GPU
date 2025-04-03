from myhdl import *

from texblock import TexBlock
from bus_arbiter import BusArbiter

@block
def TexCache(i_rstn, i_clk, i_tex_adr, i_tex_w, i_tex_h, i_tex_fmt, i_smp, o_dat, i_stb, o_ack,
             o_mem_adr, i_mem_dat, o_mem_stb, i_mem_ack):
    BLOCKS_WIDE = 8
    BLOCKS_HIGH = 8
    TOTAL_BLOCKS = BLOCKS_WIDE * BLOCKS_HIGH

    """
    Read-only 32x32 texture cache

    - i_rst: Reset signal
    - i_clk: Clock signal
    
    - i_tex_adr: Address of texture in memory
    - i_tex_w: log2 of texture width
    - i_tex_h: log2 of texture height
    - i_tex_fmt: Texture block format
    - i_smp: Texture sample position (x, y)
    - o_dat: Output sampled 2x2 texel cluster [4]

    - o_mem_adr: Output read address to backing memory
    - i_mem_dat: Input read data from backing memory
    - o_mem_stb: Output request transaction signal to backing memory
    - i_mem_ack: Input data valid signal from backing memory
    """

    tb_i_blk_adr = [Signal(intbv(0)[8:0]) for _ in range(TOTAL_BLOCKS)]
    tb_i_blk_fmt = Signal(intbv(0)[2:0])
    tb_i_smp = Signal(intbv(0)[4:0])
    tb_o_dat = [[Signal(intbv(0)[32:0]) for _ in range(4)] for _ in range(TOTAL_BLOCKS)]
    tb_i_stb = [Signal(bool(0)) for _ in range(TOTAL_BLOCKS)]
    tb_o_ack = [Signal(bool(0)) for _ in range(TOTAL_BLOCKS)]
    tb_o_mem_adr = [Signal(intbv(0)[8:0]) for _ in range(TOTAL_BLOCKS)]
    tb_i_mem_dat = [Signal(intbv(0)[32:0]) for _ in range(TOTAL_BLOCKS)]
    tb_o_mem_stb = [Signal(bool(0)) for _ in range(TOTAL_BLOCKS)]
    tb_i_mem_ack = [Signal(bool(0)) for _ in range(TOTAL_BLOCKS)]
    blocks = [TexBlock(i_rstn, i_clk, tb_i_blk_adr[i], tb_i_blk_fmt, tb_i_smp, tb_o_dat[i], tb_i_stb[i], tb_o_ack[i], tb_o_mem_adr[i], tb_i_mem_dat[i], tb_o_mem_stb[i], tb_i_mem_ack[i], ID="TB%s" % i) for i in range(TOTAL_BLOCKS)]

    arbiter_i_adr = [Signal(intbv(0)[32:]) for _ in range(TOTAL_BLOCKS)]
    arbiter_i_dat = [Signal(intbv(0)[32:]) for _ in range(TOTAL_BLOCKS)]
    arbiter_o_dat = Signal(intbv(0)[32:])
    arbiter_i_we  = [Signal(bool(0)) for _ in range(TOTAL_BLOCKS)]
    arbiter_i_stb = [Signal(bool(0)) for _ in range(TOTAL_BLOCKS)]
    arbiter_o_ack = [Signal(bool(0)) for _ in range(TOTAL_BLOCKS)]
    arbiter_o_mem_adr = Signal(intbv(0)[32:])
    arbiter_o_mem_dat = Signal(intbv(0)[32:])
    arbiter_i_mem_dat = Signal(intbv(0)[32:])
    arbiter_o_mem_we  = Signal(bool(0))
    arbiter_o_mem_stb = Signal(bool(0))
    arbiter_i_mem_ack = Signal(bool(0))
    arbiter = BusArbiter(i_rstn, i_clk, arbiter_i_adr, arbiter_i_dat, arbiter_o_dat, arbiter_i_we, arbiter_i_stb, arbiter_o_ack,
                         arbiter_o_mem_adr, arbiter_o_mem_dat, arbiter_i_mem_dat, arbiter_o_mem_we, arbiter_o_mem_stb, arbiter_i_mem_ack,
                         NUM_PORTS=TOTAL_BLOCKS)
    
    # log2 of size per block of each format (RGBA4444, RGBA8888, NXTC mode 0, and NXTC mode 1)
    _blk_shift_table = (3, 4, 1, 2)
    
    @always_comb
    def comb_logic():
        # how much comb logic is too much? asking for a friend
        # frankly most of what this is doing is routing a block address into each texture block,
        # and then piping the results of each block into the output 2x2 cluster
        # it also wires each texture block into a 4-way bus arbiter to manage each block's access to backing memory

        txw = 1 << i_tex_w
        txh = 1 << i_tex_h

        blw = txw >> 2
        blh = txh >> 2

        blw_mask = blw - 1
        blh_mask = blh - 1

        txw_mask = txw - 1
        txh_mask = txh - 1

        ####
        sx = i_smp[0]
        sy = i_smp[1]

        sx1 = (sx + 1) & txw_mask
        sy1 = (sy + 1) & txh_mask
        
        smp00 = (sx,                sy)
        smp01 = (intbv(sx1)[9:],    sy)
        smp10 = (sx,                intbv(sy1)[9:])
        smp11 = (intbv(sx1)[9:],    intbv(sy1)[9:])

        blk00 = concat(smp00[1][5:2],   smp00[0][5:2])
        blk01 = concat(smp01[1][5:2],   smp01[0][5:2])
        blk10 = concat(smp10[1][5:2],   smp10[0][5:2])
        blk11 = concat(smp11[1][5:2],   smp11[0][5:2])

        for cacheblock in range(TOTAL_BLOCKS):
            # determine which of the blocks in the cache the 2x2 cluster overlaps, so that only texture blocks that need to be sampled from are loaded
            is_blk_sampled = (blk00 == cacheblock or blk01 == cacheblock or blk10 == cacheblock or blk11 == cacheblock)
            tb_i_stb[cacheblock].next = i_stb and is_blk_sampled

        # make sure the contents of each sampled block in the 2x2 cluster is valid
        o_ack.next = tb_o_ack[blk00] and tb_o_ack[blk01] and tb_o_ack[blk10] and tb_o_ack[blk11]
        ####

        tb_i_blk_fmt.next = i_tex_fmt
        tb_i_smp.next = concat(i_smp[1][2:], i_smp[0][2:])

        ####
        blk_x0 = concat(intbv(0)[11:0], i_smp[0][9:2]) & blw_mask
        blk_x1 = (concat(intbv(0)[11:0], i_smp[0][9:2]) + 1) & blw_mask

        blk_y0 = concat(intbv(0)[11:0], i_smp[1][9:2]) & blh_mask
        blk_y1 = (concat(intbv(0)[11:0], i_smp[1][9:2]) + 1) & blh_mask

        blk00_offs = blk_x0 + (blk_y0 * blw)
        blk01_offs = blk_x1 + (blk_y0 * blw)
        blk10_offs = blk_x0 + (blk_y1 * blw)
        blk11_offs = blk_x1 + (blk_y1 * blw)

        blk_shift = _blk_shift_table[i_tex_fmt]

        blk_adr_00 = i_tex_adr + (blk00_offs << blk_shift)
        blk_adr_01 = i_tex_adr + (blk01_offs << blk_shift)
        blk_adr_10 = i_tex_adr + (blk10_offs << blk_shift)
        blk_adr_11 = i_tex_adr + (blk11_offs << blk_shift)

        # assign calculated addresses to each block
        bl0 = concat(intbv(blk_y0)[3:], intbv(blk_x0)[3:])
        bl1 = concat(intbv(blk_y0)[3:], intbv(blk_x1)[3:])
        bl2 = concat(intbv(blk_y1)[3:], intbv(blk_x0)[3:])
        bl3 = concat(intbv(blk_y1)[3:], intbv(blk_x1)[3:])

        # todo: this is an awful lot of comb logic... I should probably be clocking it but that will introduce latency...
        for i in range(TOTAL_BLOCKS):
            if bl0 == i:
                tb_i_blk_adr[i].next = blk_adr_00
            elif bl1 == i:
                tb_i_blk_adr[i].next = blk_adr_01
            elif bl2 == i:
                tb_i_blk_adr[i].next = blk_adr_10
            elif bl3 == i:
                tb_i_blk_adr[i].next = blk_adr_11
            else:
                tb_i_blk_adr[i].next = 0

        # assemble output data from blocks we sampled from
        o_dat[0].next = tb_o_dat[blk00][0]
        o_dat[1].next = tb_o_dat[blk01][1]
        o_dat[2].next = tb_o_dat[blk10][2]
        o_dat[3].next = tb_o_dat[blk11][3]
        ####
        
        for i in range(TOTAL_BLOCKS):
            arbiter_i_adr[i].next = tb_o_mem_adr[i]
            tb_i_mem_dat[i].next = arbiter_o_dat 
            arbiter_i_stb[i].next = tb_o_mem_stb[i]
            tb_i_mem_ack[i].next = arbiter_o_ack[i]
        
        o_mem_adr.next = arbiter_o_mem_adr
        arbiter_i_mem_dat.next = i_mem_dat
        o_mem_stb.next = arbiter_o_mem_stb
        arbiter_i_mem_ack.next = i_mem_ack

    return (blocks, arbiter, comb_logic)