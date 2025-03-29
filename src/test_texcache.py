import numpy as np
from myhdl import *

from clk_driver import ClkDriver
from mem import ROM
from texcache import TexCache

@block
def Top():
    rst = ResetSignal(0, active=0, isasync=True)
    clk = Signal(0)
    clk_driver = ClkDriver(clk)

    test_mem_contents = tuple(map(int, np.fromfile("test_texdata.bin", dtype='uint32')))

    test_ram_o_data = Signal(intbv(0)[32:0])
    test_ram_i_adr = Signal(intbv(0)[8:0])
    test_ram = ROM(test_ram_o_data, test_ram_i_adr, CONTENT=test_mem_contents)

    test_tx_i_tex_adr = Signal(intbv(0)[8:0])
    test_tx_i_tex_w = Signal(intbv(0)[4:0])
    test_tx_i_tex_h = Signal(intbv(0)[4:0])
    test_tx_i_tex_fmt = Signal(intbv(0)[2:0])
    test_tx_i_smp = [Signal(intbv(0)[7:0]) for _ in range(2)]
    test_tx_o_dat = [Signal(intbv(0)[32:0]) for _ in range(4)]
    test_tx_i_stb = Signal(bool(0))
    test_tx_o_ack = Signal(bool(0))
    test_tx_o_mem_adr = Signal(intbv(0)[8:0])
    test_tx_i_mem_dat = Signal(intbv(0)[32:0])
    test_tx_o_mem_stb = Signal(bool(0))
    test_tx_i_mem_ack = Signal(bool(0))
    test_tx = TexCache(rst, clk, test_tx_i_tex_adr, test_tx_i_tex_w, test_tx_i_tex_h, test_tx_i_tex_fmt, test_tx_i_smp, test_tx_o_dat, test_tx_i_stb, test_tx_o_ack,
                       test_tx_o_mem_adr, test_tx_i_mem_dat, test_tx_o_mem_stb, test_tx_i_mem_ack)
    
    @always_comb
    def drive_comb():
        test_ram_i_adr.next = test_tx_o_mem_adr
        test_tx_i_mem_dat.next = test_ram_o_data
        test_tx_i_mem_ack.next = test_tx_o_mem_stb

    @instance
    def drive_test():
        rst.next = 0
        yield delay(100)
        rst.next = 1
        yield delay(100)
        # test: sample 16x16 texture at address 0, NXTC, sample pos (3, 3)
        test_tx_i_tex_adr.next = 0
        test_tx_i_tex_w.next = 4
        test_tx_i_tex_h.next = 4
        test_tx_i_tex_fmt.next = 3
        test_tx_i_smp[0].next = 3
        test_tx_i_smp[1].next = 3
        test_tx_i_stb.next = True
        while not test_tx_o_ack:
            yield delay(20)
        test_tx_i_stb.next = False
        print("Output: %s, %s, %s, %s" % (test_tx_o_dat[0], test_tx_o_dat[1], test_tx_o_dat[2], test_tx_o_dat[3]))

    return clk_driver, drive_test, drive_comb, test_ram, test_tx

inst = Top()
inst.run_sim(20 * 1600)