from myhdl import block, delay, always, always_comb, Signal, ResetSignal, intbv, instance, now
from PIL import Image

from clk_driver import ClkDriver
from tri_raster import TriRaster
from mem import RAM

def unpack_rgb(col):
    r = col & 0xFF
    g = (col >> 8) & 0xFF
    b = (col >> 16) & 0xFF
    return (r, g, b)

@block
def Top():
    rst = ResetSignal(0, active=0, isasync=True)
    clk = Signal(0)
    clk_driver = ClkDriver(clk)
    
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

    tri_raster_en = Signal(bool(0))
    tri_raster_busy = Signal(bool(0))
    tri_raster_wr_en_rgb = [Signal(bool(0)) for _ in range(4)]
    tri_raster_wr_data_rgb = [Signal(intbv(0)[32:0]) for _ in range(4)]
    tri_raster_wr_en_ds = [Signal(bool(0)) for _ in range(4)]
    tri_raster_wr_data_ds = [Signal(intbv(0)[32:0]) for _ in range(4)]
    tri_raster_wr_pos = [Signal(intbv(0)[32:0]) for _ in range(2)]
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
    tri_raster = TriRaster(rst, clk, tri_raster_v0, tri_raster_v1, tri_raster_v2,
                           tri_raster_col_init, tri_raster_col_dx, tri_raster_col_dy,
                           tri_raster_1ow_init, tri_raster_1ow_dx, tri_raster_1ow_dy,
                           tri_raster_sow_init, tri_raster_sow_dx, tri_raster_sow_dy,
                           tri_raster_tow_init, tri_raster_tow_dx, tri_raster_tow_dy,
                           tri_raster_zow_init, tri_raster_zow_dx, tri_raster_zow_dy,
                           tri_raster_en, tri_raster_busy,
                           tri_raster_wr_en_rgb, tri_raster_wr_data_rgb,
                           tri_raster_wr_en_ds, tri_raster_wr_data_ds,
                           tri_raster_wr_pos, DIM = 32)

    buffer_color = Image.new('RGB', (32, 32))
    for j in range(0,32):
        for i in range(0,32):
            buffer_color.putpixel((i, j), (64, 128, 255))

    buffer_depth = Image.new('L', (32, 32))
    for j in range(0,32):
        for i in range(0,32):
            buffer_depth.putpixel((i, j), 255)

    @always_comb
    def drive_comb():
        colorbuffer_addr.next = depthbuffer_addr.next = tri_raster_wr_pos[0] + (tri_raster_wr_pos[1] << 4)
        for i in range(4):
            colorbuffer_din[i].next = tri_raster_wr_data_rgb[i]
            colorbuffer_we[i].next = tri_raster_wr_en_rgb[i]
            depthbuffer_din[i].next = tri_raster_wr_data_ds[i]
            depthbuffer_we[i].next = tri_raster_wr_en_ds[i]

    @always(clk.posedge)
    def write_img():
        for i in range(4):
            if tri_raster_wr_en_rgb[i]:
                px = tri_raster_wr_pos[0] << 1
                py = tri_raster_wr_pos[1] << 1
                px += i % 2
                py += i >> 1 
                col = unpack_rgb(tri_raster_wr_data_rgb[i])
                buffer_color.putpixel((px, py), col)
            if tri_raster_wr_en_ds[i]:
                px = tri_raster_wr_pos[0] << 1
                py = tri_raster_wr_pos[1] << 1
                px += i % 2
                py += i >> 1
                depth = int(tri_raster_wr_data_ds[i])
                buffer_depth.putpixel((px, py), depth >> 16)

    @instance
    def drive_test():
        rst.next = 0
        yield delay(100)
        rst.next = 1
        yield delay(100)
        tri_raster_v0[0].next = 0
        tri_raster_v0[1].next = 0
        tri_raster_v1[0].next = 32
        tri_raster_v1[1].next = 0
        tri_raster_v2[0].next = 16
        tri_raster_v2[1].next = 32
        tri_raster_col_init[0].next = (255 << 12)
        tri_raster_col_init[1].next = 0
        tri_raster_col_init[2].next = 0
        tri_raster_col_init[3].next = (255 << 12)
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
        tri_raster_sow_dy.next = int(0.03125 * 0.5 * 4095)
        tri_raster_tow_init.next = 0
        tri_raster_tow_dx.next = int(0.03125 * 4095)
        tri_raster_tow_dy.next = int(-0.03125 * 0.5 * 4095)
        tri_raster_en.next = 1
        yield delay(20)
        tri_raster_en.next = 0
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
            tri_raster, drive_comb, drive_test, write_img)

inst = Top()
inst.run_sim(20 * 1600)