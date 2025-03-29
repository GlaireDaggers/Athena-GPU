from myhdl import *

from texblock import TexBlock
from bus_arbiter import BusArbiter

@block
def TexCache(i_rstn, i_clk, i_tex_adr, i_tex_w, i_tex_h, i_tex_fmt, i_smp, o_dat, i_stb, o_ack,
             o_mem_adr, i_mem_dat, o_mem_stb, i_mem_ack):
    """
    Read-only 8x8 texture cache

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

    tb_i_blk_adr = [Signal(intbv(0)[8:0]) for _ in range(4)]
    tb_i_blk_fmt = Signal(intbv(0)[2:0])
    tb_i_smp = Signal(intbv(0)[4:0])
    tb_o_dat = [[Signal(intbv(0)[32:0]) for _ in range(4)] for _ in range(4)]
    tb_i_stb = [Signal(bool(0)) for _ in range(4)]
    tb_o_ack = [Signal(bool(0)) for _ in range(4)]
    tb_o_mem_adr = [Signal(intbv(0)[8:0]) for _ in range(4)]
    tb_i_mem_dat = [Signal(intbv(0)[32:0]) for _ in range(4)]
    tb_o_mem_stb = [Signal(bool(0)) for _ in range(4)]
    tb_i_mem_ack = [Signal(bool(0)) for _ in range(4)]
    blocks = [TexBlock(i_rstn, i_clk, tb_i_blk_adr[i], tb_i_blk_fmt, tb_i_smp, tb_o_dat[i], tb_i_stb[i], tb_o_ack[i], tb_o_mem_adr[i], tb_i_mem_dat[i], tb_o_mem_stb[i], tb_i_mem_ack[i], ID="TB%s" % i) for i in range(4)]

    arbiter_i_adr = [Signal(intbv(0)[32:]) for _ in range(4)]
    arbiter_i_dat = [Signal(intbv(0)[32:]) for _ in range(4)]
    arbiter_o_dat = [Signal(intbv(0)[32:]) for _ in range(4)]
    arbiter_i_we  = [Signal(bool(0)) for _ in range(4)]
    arbiter_i_stb = [Signal(bool(0)) for _ in range(4)]
    arbiter_o_ack = [Signal(bool(0)) for _ in range(4)]
    arbiter_o_mem_adr = Signal(intbv(0)[32:])
    arbiter_o_mem_dat = Signal(intbv(0)[32:])
    arbiter_i_mem_dat = Signal(intbv(0)[32:])
    arbiter_o_mem_we  = Signal(bool(0))
    arbiter_o_mem_stb = Signal(bool(0))
    arbiter_i_mem_ack = Signal(bool(0))
    arbiter = BusArbiter(i_rstn, i_clk, arbiter_i_adr, arbiter_i_dat, arbiter_o_dat, arbiter_i_we, arbiter_i_stb, arbiter_o_ack,
                         arbiter_o_mem_adr, arbiter_o_mem_dat, arbiter_i_mem_dat, arbiter_o_mem_we, arbiter_o_mem_stb, arbiter_i_mem_ack)
    
    _blk_shift_table = (3, 4, 2, 1)
    
    @always_comb
    def comb_logic():
        # how much comb logic is too much? asking for a friend
        # frankly most of what this is doing is routing a block address into each texture block,
        # and then piping the results of each block into the output 2x2 cluster
        # it also wires each texture block into a 4-way bus arbiter to manage each block's access to backing memory

        ####
        sx = i_smp[0]
        sy = i_smp[1]
        
        smp00 = (sx,                    sy)
        smp01 = (intbv(sx + 1)[9:],     sy)
        smp10 = (sx,                    intbv(sy + 1)[9:])
        smp11 = (intbv(sx + 1)[9:],     intbv(sy + 1)[9:])
        
        blk00 = concat(smp00[1][2],     smp00[0][2])
        blk01 = concat(smp01[1][2],     smp01[0][2])
        blk10 = concat(smp10[1][2],     smp10[0][2])
        blk11 = concat(smp11[1][2],     smp11[0][2])

        # determine which blocks the 2x2 cluster overlaps so that only texture blocks that need to be sampled from are loaded
        is_blk_0 = (blk00 == 0 or blk01 == 0 or blk10 == 0 or blk11 == 0)
        is_blk_1 = (blk00 == 1 or blk01 == 1 or blk10 == 1 or blk11 == 1)
        is_blk_2 = (blk00 == 2 or blk01 == 2 or blk10 == 2 or blk11 == 2)
        is_blk_3 = (blk00 == 3 or blk01 == 3 or blk10 == 3 or blk11 == 3)

        tb_i_stb[0].next = i_stb and is_blk_0
        tb_i_stb[1].next = i_stb and is_blk_1
        tb_i_stb[2].next = i_stb and is_blk_2
        tb_i_stb[3].next = i_stb and is_blk_3

        o_ack.next = tb_o_ack[blk00] and tb_o_ack[blk01] and tb_o_ack[blk10] and tb_o_ack[blk11]
        ####

        tb_i_blk_fmt.next = i_tex_fmt
        tb_i_smp.next = concat(i_smp[1][2:], i_smp[0][2:])

        ####
        blw = i_tex_w >> 2
        blh = i_tex_h >> 2

        blw_mask = (1 << blw) - 1
        blh_mask = (1 << blh) - 1

        blk_x0 = concat(intbv(0)[11:0], i_smp[0][9:2]) & blw_mask
        blk_x1 = (concat(intbv(0)[11:0], i_smp[0][9:2]) + 1) & blw_mask

        blk_y0 = concat(intbv(0)[11:0], i_smp[1][9:2]) & blh_mask
        blk_y1 = (concat(intbv(0)[11:0], i_smp[1][9:2]) + 1) & blh_mask

        blk00_offs = blk_x0 + (blk_y0 << blw)
        blk01_offs = blk_x1 + (blk_y0 << blw)
        blk10_offs = blk_x0 + (blk_y1 << blw)
        blk11_offs = blk_x1 + (blk_y1 << blw)
        
        blk_shift = _blk_shift_table[i_tex_fmt]

        # assign addresses to each block
        if blk00 == 0:
            tb_i_blk_adr[0].next = i_tex_adr + (blk00_offs << blk_shift)
            tb_i_blk_adr[1].next = i_tex_adr + (blk01_offs << blk_shift)
            tb_i_blk_adr[2].next = i_tex_adr + (blk10_offs << blk_shift)
            tb_i_blk_adr[3].next = i_tex_adr + (blk11_offs << blk_shift)
        elif blk00 == 1:
            tb_i_blk_adr[1].next = i_tex_adr + (blk00_offs << blk_shift)
            tb_i_blk_adr[0].next = i_tex_adr + (blk01_offs << blk_shift)
            tb_i_blk_adr[3].next = i_tex_adr + (blk10_offs << blk_shift)
            tb_i_blk_adr[2].next = i_tex_adr + (blk11_offs << blk_shift)
        elif blk00 == 2:
            tb_i_blk_adr[2].next = i_tex_adr + (blk00_offs << blk_shift)
            tb_i_blk_adr[3].next = i_tex_adr + (blk01_offs << blk_shift)
            tb_i_blk_adr[0].next = i_tex_adr + (blk10_offs << blk_shift)
            tb_i_blk_adr[1].next = i_tex_adr + (blk11_offs << blk_shift)
        elif blk00 == 3:
            tb_i_blk_adr[3].next = i_tex_adr + (blk00_offs << blk_shift)
            tb_i_blk_adr[2].next = i_tex_adr + (blk01_offs << blk_shift)
            tb_i_blk_adr[1].next = i_tex_adr + (blk10_offs << blk_shift)
            tb_i_blk_adr[0].next = i_tex_adr + (blk11_offs << blk_shift)

        # assemble output data from blocks we sampled from
        o_dat[0].next = tb_o_dat[blk00][0]
        o_dat[1].next = tb_o_dat[blk01][1]
        o_dat[2].next = tb_o_dat[blk10][2]
        o_dat[3].next = tb_o_dat[blk11][3]
        ####
        
        for i in range(4):
            arbiter_i_adr[i].next = tb_o_mem_adr[i]
            tb_i_mem_dat[i].next = arbiter_o_dat[i] 
            arbiter_i_stb[i].next = tb_o_mem_stb[i]
            tb_i_mem_ack[i].next = arbiter_o_ack[i]
        o_mem_adr.next = arbiter_o_mem_adr
        arbiter_i_mem_dat.next = i_mem_dat
        o_mem_stb.next = arbiter_o_mem_stb
        arbiter_i_mem_ack.next = i_mem_ack

    return blocks[0], blocks[1], blocks[2], blocks[3], arbiter, comb_logic