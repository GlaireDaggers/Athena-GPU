import numpy as np
from myhdl import block, delay, always, always_comb, Signal, ResetSignal, intbv, instance, now
from PIL import Image

from clk_driver import ClkDriver
from tri_raster import TriRaster
from texcache import TexCache
from texsample import TexSampler
from mem import RAM, ROM

def unpack_rgba(col):
    r = col & 0xFF
    g = (col >> 8) & 0xFF
    b = (col >> 16) & 0xFF
    a = (col >> 24) & 0xFF
    return (r, g, b, a)

@block
def Top():
    rst = ResetSignal(0, active=0, isasync=True)
    clk = Signal(0)
    clk_driver = ClkDriver(clk)

    test_tex_rom_contents = tuple(map(int, np.fromfile("util/test_crate_2_nxtc.bin", dtype='uint32')))
    test_tex_rom_o_data = Signal(intbv(0)[32:0])
    test_tex_rom_i_adr = Signal(intbv(0)[8:0])
    test_tex_rom = ROM(test_tex_rom_o_data, test_tex_rom_i_adr, CONTENT=test_tex_rom_contents)

    test_tx_i_tex_adr = Signal(intbv(0)[8:0])
    test_tx_i_tex_w = Signal(intbv(0)[4:0])
    test_tx_i_tex_h = Signal(intbv(0)[4:0])
    test_tx_i_tex_fmt = Signal(intbv(0)[2:0])
    test_tx_i_smp = [Signal(intbv(0)[32:0]) for _ in range(2)]
    test_tx_o_dat = [Signal(intbv(0)[32:0]) for _ in range(4)]
    test_tx_i_stb = Signal(bool(0))
    test_tx_o_ack = Signal(bool(0))
    test_tx_o_mem_adr = Signal(intbv(0)[8:0])
    test_tx_i_mem_dat = Signal(intbv(0)[32:0])
    test_tx_o_mem_stb = Signal(bool(0))
    test_tx_i_mem_ack = Signal(bool(0))
    test_tx = TexCache(rst, clk, test_tx_i_tex_adr, test_tx_i_tex_w, test_tx_i_tex_h, test_tx_i_tex_fmt, test_tx_i_smp, test_tx_o_dat, test_tx_i_stb, test_tx_o_ack,
                       test_tx_o_mem_adr, test_tx_i_mem_dat, test_tx_o_mem_stb, test_tx_i_mem_ack)
    
    smp_i_stb = Signal(bool(0))
    smp_i_st = [Signal(intbv(0)[32:].signed()) for _ in range(2)]
    smp_i_w = Signal(intbv(0)[4:0])
    smp_i_h = Signal(intbv(0)[4:0])
    smp_i_clmp_s = Signal(bool(0))
    smp_i_clmp_t = Signal(bool(0))
    smp_i_flt = Signal(bool(0))
    smp_o_dat = Signal(intbv(0)[32:0])
    smp_o_ack = Signal(bool(0))
    smp_o_tc_stb = Signal(bool(0))
    smp_o_tc_smp = [Signal(intbv(0)[32:0]) for _ in range(2)]
    smp_i_tc_dat = [Signal(intbv(0)[32:0]) for _ in range(4)]
    smp_i_tc_ack = Signal(bool(0))
    test_smp = TexSampler(rst, clk, smp_i_stb, smp_i_st, smp_i_w, smp_i_h, smp_i_clmp_s, smp_i_clmp_t, smp_i_flt, smp_o_dat, smp_o_ack,
                          smp_o_tc_stb, smp_o_tc_smp, smp_i_tc_dat, smp_i_tc_ack)
    
    colorbuffer_addr = Signal(intbv(0)[32:0])
    colorbuffer_dout = [Signal(intbv(0)[32:0]) for _ in range(4)]
    colorbuffer_din = [Signal(intbv(0)[32:0]) for _ in range(4)]
    colorbuffer_we = [Signal(bool(0)) for _ in range(4)]
    colorbuffer0 = RAM(colorbuffer_dout[0], colorbuffer_din[0], colorbuffer_addr, colorbuffer_we[0], clk, WIDTH=32, DEPTH=256, ID="colorbuffer_0")
    colorbuffer1 = RAM(colorbuffer_dout[1], colorbuffer_din[1], colorbuffer_addr, colorbuffer_we[1], clk, WIDTH=32, DEPTH=256, ID="colorbuffer_1")
    colorbuffer2 = RAM(colorbuffer_dout[2], colorbuffer_din[2], colorbuffer_addr, colorbuffer_we[2], clk, WIDTH=32, DEPTH=256, ID="colorbuffer_2")
    colorbuffer3 = RAM(colorbuffer_dout[3], colorbuffer_din[3], colorbuffer_addr, colorbuffer_we[3], clk, WIDTH=32, DEPTH=256, ID="colorbuffer_3")

    depthbuffer_addr = Signal(intbv(0)[32:0])
    depthbuffer_dout = [Signal(intbv(0)[32:0]) for _ in range(4)]
    depthbuffer_din = [Signal(intbv(0)[32:0]) for _ in range(4)]
    depthbuffer_we = [Signal(bool(0)) for _ in range(4)]
    depthbuffer0 = RAM(depthbuffer_dout[0], depthbuffer_din[0], depthbuffer_addr, depthbuffer_we[0], clk, WIDTH=32, DEPTH=256, ID="depthbuffer_0")
    depthbuffer1 = RAM(depthbuffer_dout[1], depthbuffer_din[1], depthbuffer_addr, depthbuffer_we[1], clk, WIDTH=32, DEPTH=256, ID="depthbuffer_1")
    depthbuffer2 = RAM(depthbuffer_dout[2], depthbuffer_din[2], depthbuffer_addr, depthbuffer_we[2], clk, WIDTH=32, DEPTH=256, ID="depthbuffer_2")
    depthbuffer3 = RAM(depthbuffer_dout[3], depthbuffer_din[3], depthbuffer_addr, depthbuffer_we[3], clk, WIDTH=32, DEPTH=256, ID="depthbuffer_3")

    tri_raster_tri_stb = Signal(bool(0))
    tri_raster_fill_stb = Signal(bool(0))
    tri_raster_busy = Signal(bool(0))
    tri_raster_wr_en_rgb = [Signal(bool(0)) for _ in range(4)]
    tri_raster_wr_data_rgb = [Signal(intbv(0)[32:0]) for _ in range(4)]
    tri_raster_wr_en_d = [Signal(bool(0)) for _ in range(4)]
    tri_raster_wr_data_d = [Signal(intbv(0)[32:0]) for _ in range(4)]
    tri_raster_wr_pos = [Signal(intbv(0)[32:0]) for _ in range(2)]
    tri_raster_rd_data_rgb = [Signal(intbv(0)[32:0]) for _ in range(4)]
    tri_raster_rd_data_d = [Signal(intbv(0)[32:0]) for _ in range(4)]
    tri_raster_v0 = [Signal(intbv(0)[32:0].signed()) for _ in range(2)]
    tri_raster_v1 = [Signal(intbv(0)[32:0].signed()) for _ in range(2)]
    tri_raster_v2 = [Signal(intbv(0)[32:0].signed()) for _ in range(2)]
    tri_raster_col_init = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]
    tri_raster_col_dx = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]
    tri_raster_col_dy = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]
    tri_raster_1ow_init = Signal(intbv(0)[32:0].signed())
    tri_raster_1ow_dx = Signal(intbv(0)[32:0].signed())
    tri_raster_1ow_dy = Signal(intbv(0)[32:0].signed())
    tri_raster_sow_init = Signal(intbv(0)[32:0].signed())
    tri_raster_sow_dx = Signal(intbv(0)[32:0].signed())
    tri_raster_sow_dy = Signal(intbv(0)[32:0].signed())
    tri_raster_tow_init = Signal(intbv(0)[32:0].signed())
    tri_raster_tow_dx = Signal(intbv(0)[32:0].signed())
    tri_raster_tow_dy = Signal(intbv(0)[32:0].signed())
    tri_raster_zow_init = Signal(intbv(0)[32:0].signed())
    tri_raster_zow_dx = Signal(intbv(0)[32:0].signed())
    tri_raster_zow_dy = Signal(intbv(0)[32:0].signed())
    tri_raster_tex_en = Signal(bool(0))
    tri_raster_dtest_en = Signal(bool(0))
    tri_raster_dcmp = Signal(intbv(0)[3:0])
    tri_raster_bl_en = Signal(bool(0))
    tri_raster_bl_src = Signal(intbv(0)[4:0])
    tri_raster_bl_dst = Signal(intbv(0)[4:0])
    tri_raster_bl_op = Signal(0)
    tri_raster_fog_en = Signal(bool(0))
    tri_raster_fog_col = Signal(intbv(0)[32:])
    tri_raster_o_smp_stb = Signal(bool(0))
    tri_raster_o_smp_st = [Signal(intbv(0)[32:0].signed()) for _ in range(2)]
    tri_raster_i_smp_dat = Signal(intbv(0)[32:0])
    tri_raster_i_smp_ack = Signal(bool(0))
    tri_raster_i_fog_tbl = [Signal(intbv(0)[8:0]) for _ in range(64)]
    tri_raster = TriRaster(rst, clk, tri_raster_v0, tri_raster_v1, tri_raster_v2,
                           tri_raster_col_init, tri_raster_col_dx, tri_raster_col_dy,
                           tri_raster_1ow_init, tri_raster_1ow_dx, tri_raster_1ow_dy,
                           tri_raster_sow_init, tri_raster_sow_dx, tri_raster_sow_dy,
                           tri_raster_tow_init, tri_raster_tow_dx, tri_raster_tow_dy,
                           tri_raster_zow_init, tri_raster_zow_dx, tri_raster_zow_dy,
                           tri_raster_tex_en, tri_raster_dtest_en, tri_raster_dcmp,
                           tri_raster_bl_en, tri_raster_bl_src, tri_raster_bl_dst, tri_raster_bl_op,
                           tri_raster_fog_en, tri_raster_fog_col,
                           tri_raster_tri_stb, tri_raster_fill_stb, tri_raster_busy,
                           tri_raster_wr_en_rgb, tri_raster_wr_data_rgb,
                           tri_raster_wr_en_d, tri_raster_wr_data_d,
                           tri_raster_wr_pos,
                           tri_raster_rd_data_rgb, tri_raster_rd_data_d,
                           tri_raster_o_smp_stb, tri_raster_o_smp_st, tri_raster_i_smp_dat, tri_raster_i_smp_ack,
                           tri_raster_i_fog_tbl,
                           DIM = 32)

    buffer_color = Image.new('RGBA', (32, 32))
    for j in range(0,32):
        for i in range(0,32):
            buffer_color.putpixel((i, j), (0, 0, 0, 0))

    buffer_depth = Image.new('L', (32, 32))
    for j in range(0,32):
        for i in range(0,32):
            buffer_depth.putpixel((i, j), 0)

    @always_comb
    def drive_comb():
        test_tex_rom_i_adr.next = test_tx_o_mem_adr
        test_tx_i_mem_dat.next = test_tex_rom_o_data
        test_tx_i_mem_ack.next = test_tx_o_mem_stb

        smp_i_w.next = test_tx_i_tex_w
        smp_i_h.next = test_tx_i_tex_h

        test_tx_i_smp[0].next = smp_o_tc_smp[0]
        test_tx_i_smp[1].next = smp_o_tc_smp[1]

        smp_i_tc_ack.next = test_tx_o_ack
        test_tx_i_stb.next = smp_o_tc_stb

        for i in range(4):
            smp_i_tc_dat[i].next = test_tx_o_dat[i]

        smp_i_stb.next = tri_raster_o_smp_stb
        smp_i_st[0].next = tri_raster_o_smp_st[0]
        smp_i_st[1].next = tri_raster_o_smp_st[1]
        tri_raster_i_smp_ack.next = smp_o_ack
        tri_raster_i_smp_dat.next = smp_o_dat

        colorbuffer_addr.next = depthbuffer_addr.next = tri_raster_wr_pos[0] + (tri_raster_wr_pos[1] << 4)
        for i in range(4):
            colorbuffer_din[i].next = tri_raster_wr_data_rgb[i]
            colorbuffer_we[i].next = tri_raster_wr_en_rgb[i]
            depthbuffer_din[i].next = tri_raster_wr_data_d[i]
            depthbuffer_we[i].next = tri_raster_wr_en_d[i]
            tri_raster_rd_data_rgb[i].next = colorbuffer_dout[i]
            tri_raster_rd_data_d[i].next = depthbuffer_dout[i]

    @always(clk.posedge)
    def write_img():
        for i in range(4):
            if tri_raster_wr_en_rgb[i]:
                px = tri_raster_wr_pos[0] << 1
                py = tri_raster_wr_pos[1] << 1
                px += i % 2
                py += i >> 1 
                col = unpack_rgba(tri_raster_wr_data_rgb[i])
                buffer_color.putpixel((px, py), col)
            if tri_raster_wr_en_d[i]:
                px = tri_raster_wr_pos[0] << 1
                py = tri_raster_wr_pos[1] << 1
                px += i % 2
                py += i >> 1
                depth = int(tri_raster_wr_data_d[i])
                buffer_depth.putpixel((px, py), depth >> 16)

    @instance
    def drive_test():
        rst.next = 0
        yield delay(100)
        rst.next = 1
        yield delay(100)
        # clear tile buffer
        tri_raster_col_init[0].next = (64 << 12)
        tri_raster_col_init[1].next = (128 << 12)
        tri_raster_col_init[2].next = (255 << 12)
        tri_raster_col_init[3].next = (255 << 12)
        tri_raster_zow_init.next = 0xFFFFFF
        tri_raster_fill_stb.next = True
        #
        yield delay(20)
        tri_raster_fill_stb.next = 0
        begin_time = now()
        while tri_raster_busy:
            yield delay(20)
        end_time = now()
        cycle_time = int((end_time - begin_time) / 20)
        print("Cleared buffer in %s cycles" % cycle_time)
        # test triangle
        tri_raster_v0[0].next = 0
        tri_raster_v0[1].next = 0
        tri_raster_v1[0].next = 32
        tri_raster_v1[1].next = 0
        tri_raster_v2[0].next = 16
        tri_raster_v2[1].next = 32
        tri_raster_col_init[0].next = (255 << 12)
        tri_raster_col_init[1].next = 0
        tri_raster_col_init[2].next = 0
        tri_raster_col_init[3].next = (128 << 12)
        tri_raster_col_dx[0].next = int(-7.96875 * 4096)
        tri_raster_col_dx[1].next = int(7.96875 * 4096)
        tri_raster_col_dx[2].next = 0
        tri_raster_col_dx[3].next = 0
        tri_raster_col_dy[0].next = int(-7.96875 * 0.5 * 4096)
        tri_raster_col_dy[1].next = int(-7.96875 * 0.5 * 4096)
        tri_raster_col_dy[2].next = int(7.96875 * 4096)
        tri_raster_col_dy[3].next = 0
        tri_raster_1ow_init.next = int(1.0 * 4096)
        tri_raster_1ow_dx.next = 0
        tri_raster_1ow_dy.next = 0
        tri_raster_zow_init.next = 0
        tri_raster_zow_dx.next = int(0.03125 * 0.5 * (1 << 24))
        tri_raster_zow_dy.next = int(0.03125 * 0.25 * (1 << 24))
        tri_raster_sow_init.next = 0
        tri_raster_sow_dx.next = int(0.03125 * 4095)
        tri_raster_sow_dy.next = int(-0.03125 * 0.5 * 4095)
        tri_raster_tow_init.next = 0
        tri_raster_tow_dx.next = 0
        tri_raster_tow_dy.next = int(0.03125 * 4095)
        # enable depth test, less-or-equal
        tri_raster_dtest_en.next = True
        tri_raster_dcmp.next = 6
        # enable blending, src factor = src alpha, dst factor = inv src alpha, blend op = add
        tri_raster_bl_en.next = True
        tri_raster_bl_src.next = 3
        tri_raster_bl_dst.next = 7
        tri_raster_bl_op.next = 0
        # setup fog table
        for i in range(64):
            if i > 16:
                tri_raster_i_fog_tbl[i].next = min((i - 16) << 4, 255)
        # enable fog, color = (128, 128, 128)
        tri_raster_fog_en.next = True
        tri_raster_fog_col.next = 0x808080
        # test texture: 32x32 texture at address 0, NXTC mode 0, wrap S, wrap T, bilinear filtering
        test_tx_i_tex_adr.next = 0
        test_tx_i_tex_w.next = 5
        test_tx_i_tex_h.next = 5
        test_tx_i_tex_fmt.next = 2
        smp_i_flt.next = True
        smp_i_clmp_s.next = True
        smp_i_clmp_t.next = True
        #
        tri_raster_tex_en.next = 1
        tri_raster_tri_stb.next = 1
        yield delay(20)
        tri_raster_tri_stb.next = 0
        begin_time = now()
        while tri_raster_busy:
            yield delay(20)
        end_time = now()
        cycle_time = int((end_time - begin_time) / 20)
        print("Finished in %s cycles" % cycle_time)

        buffer_color.save("test.png")
        buffer_depth.save("test_depth.png")

    return (clk_driver,
            colorbuffer0, colorbuffer1, colorbuffer2, colorbuffer3,
            depthbuffer0, depthbuffer1, depthbuffer2, depthbuffer3,
            test_tex_rom, test_tx, test_smp,
            tri_raster, drive_comb, drive_test, write_img)

inst = Top()
inst.run_sim(20 * 6400)