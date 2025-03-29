import numpy as np
from myhdl import *

from clk_driver import ClkDriver
from mem import ROM
from texblock import TexBlock

@block
def Top():
    rst = ResetSignal(0, active=0, isasync=True)
    clk = Signal(0)
    clk_driver = ClkDriver(clk)

    test_mem_contents = tuple(map(int, np.fromfile("test_texdata.bin", dtype='uint32')))

    test_ram_o_data = Signal(intbv(0)[32:0])
    test_ram_i_adr = Signal(intbv(0)[8:0])
    test_ram = ROM(test_ram_o_data, test_ram_i_adr, CONTENT=test_mem_contents)

    test_tb_i_blk_adr = Signal(intbv(0)[8:0])
    test_tb_i_blk_fmt = Signal(intbv(0)[2:0])
    test_tb_i_smp = Signal(intbv(0)[4:0])
    test_tb_o_dat = [Signal(intbv(0)[32:0]) for _ in range(4)]
    test_tb_i_stb = Signal(bool(0))
    test_tb_o_ack = Signal(bool(0))
    test_tb_o_mem_adr = Signal(intbv(0)[8:0])
    test_tb_i_mem_dat = Signal(intbv(0)[32:0])
    test_tb_o_mem_stb = Signal(bool(0))
    test_tb_i_mem_ack = Signal(bool(0))
    test_tb = TexBlock(rst, clk, test_tb_i_blk_adr, test_tb_i_blk_fmt, test_tb_i_smp, test_tb_o_dat, test_tb_i_stb, test_tb_o_ack,
                          test_tb_o_mem_adr, test_tb_i_mem_dat, test_tb_o_mem_stb, test_tb_i_mem_ack)
    
    @always_comb
    def drive_comb():
        test_ram_i_adr.next = test_tb_o_mem_adr
        test_tb_i_mem_dat.next = test_ram_o_data
        test_tb_i_mem_ack.next = test_tb_o_mem_stb

    @instance
    def drive_test():
        rst.next = 0
        yield delay(100)
        rst.next = 1
        yield delay(100)
        # test: read something from block at address 4, format NXTC, sample offset (1, 2)
        test_tb_i_blk_adr.next = 4
        test_tb_i_blk_fmt.next = 3
        test_tb_i_smp.next = 1 + (2 << 2)
        test_tb_i_stb.next = True
        while not test_tb_o_ack:
            yield delay(20)
        test_tb_i_stb.next = False
        print("Output: %s, %s, %s, %s" % (test_tb_o_dat[0], test_tb_o_dat[1], test_tb_o_dat[2], test_tb_o_dat[3]))

    return clk_driver, drive_test, drive_comb, test_ram, test_tb

inst = Top()
inst.run_sim(20 * 1600)