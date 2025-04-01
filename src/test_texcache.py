import numpy as np
from myhdl import *
from PIL import Image

from clk_driver import ClkDriver
from mem import ROM
from texcache import TexCache
from texsample import TexSampler

@block
def Top():
    rst = ResetSignal(0, active=0, isasync=True)
    clk = Signal(0)
    clk_driver = ClkDriver(clk)

    test_mem_contents = tuple(map(int, np.fromfile("test_texdata_2.bin", dtype='uint32')))

    test_ram_o_data = Signal(intbv(0)[32:0])
    test_ram_i_adr = Signal(intbv(0)[8:0])
    test_ram = ROM(test_ram_o_data, test_ram_i_adr, CONTENT=test_mem_contents)

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

    test_img = Image.new('RGB', (32, 32))

    @always_comb
    def drive_comb():
        test_ram_i_adr.next = test_tx_o_mem_adr
        test_tx_i_mem_dat.next = test_ram_o_data
        test_tx_i_mem_ack.next = test_tx_o_mem_stb

        smp_i_w.next = test_tx_i_tex_w
        smp_i_h.next = test_tx_i_tex_h

        test_tx_i_smp[0].next = smp_o_tc_smp[0]
        test_tx_i_smp[1].next = smp_o_tc_smp[1]

        smp_i_tc_ack.next = test_tx_o_ack
        test_tx_i_stb.next = smp_o_tc_stb

        for i in range(4):
            smp_i_tc_dat[i].next = test_tx_o_dat[i]

    @instance
    def drive_test():
        rst.next = 0
        yield delay(100)
        rst.next = 1
        yield delay(100)
        # test: sample 8x8 texture at address 0, NXTC mode 0, clamp S, wrap T, bilinear filtering
        test_tx_i_tex_adr.next = 0
        test_tx_i_tex_w.next = 3
        test_tx_i_tex_h.next = 3
        test_tx_i_tex_fmt.next = 2
        smp_i_flt.next = True
        smp_i_clmp_s.next = True
        smp_i_clmp_t.next = False

        for j in range(32):
            for i in range(32):
                s = (i / 16.0) + (1.0 / 16.0 * 0.5) - 0.5
                t = (j / 16.0) + (1.0 / 16.0 * 0.5) - 0.5
                smp_i_st[0].next = int(s * 4096)
                smp_i_st[1].next = int(t * 4096)
                smp_i_stb.next = True
                while not smp_o_ack:
                    yield delay(20)
                smp_i_stb.next = False
                r = smp_o_dat[8:0]
                g = smp_o_dat[16:8]
                b = smp_o_dat[24:16]
                test_img.putpixel((i, j), (r, g, b))
                yield delay(20)
        
        test_img.save("test_texsample.png")
        print("%s Finished" % now())

    return clk_driver, drive_test, drive_comb, test_ram, test_smp, test_tx

inst = Top()
inst.run_sim(20 * 4000)