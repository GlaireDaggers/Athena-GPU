import numpy as np
from myhdl import *

from clk_driver import ClkDriver
from mem import RAM
from memcache import MemCache

@block
def Top():
    rst = ResetSignal(0, active=0, isasync=True)
    clk = Signal(0)
    clk_driver = ClkDriver(clk)

    test_ram_o_data = Signal(intbv(0)[32:0])
    test_ram_i_data = Signal(intbv(0)[32:0])
    test_ram_i_adr = Signal(intbv(0)[8:0])
    test_ram_i_we = Signal(bool(0))
    test_ram = RAM(test_ram_o_data, test_ram_i_data, test_ram_i_adr, test_ram_i_we, clk, WIDTH=32, DEPTH=256)

    test_cache_i_adr = Signal(intbv(0)[8:0])
    test_cache_o_dat = Signal(intbv(0)[32:0])
    test_cache_i_stb = Signal(bool(0))
    test_cache_o_ack = Signal(bool(0))
    test_cache_o_mem_adr = Signal(intbv(0)[8:0])
    test_cache_i_mem_dat = Signal(intbv(0)[32:0])
    test_cache_o_mem_stb = Signal(bool(0))
    test_cache_i_mem_ack = Signal(bool(0))
    test_cache = MemCache(rst, clk, test_cache_i_adr, test_cache_o_dat, test_cache_i_stb, test_cache_o_ack,
                          test_cache_o_mem_adr, test_cache_i_mem_dat, test_cache_o_mem_stb, test_cache_i_mem_ack,
                          WIDTH=32, ADRBITS=32, IDXBITS=4)
    
    @always_comb
    def drive_comb():
        test_ram_i_adr.next = test_cache_o_mem_adr
        test_cache_i_mem_dat.next = test_ram_o_data
        test_cache_i_mem_ack.next = test_cache_o_mem_stb

    @instance
    def drive_test():
        rst.next = 0
        yield delay(100)
        rst.next = 1
        yield delay(100)
        # test: read something from address 0
        test_cache_i_adr.next = 0
        test_cache_i_stb.next = True
        while not test_cache_o_ack:
            yield delay(20)
        test_cache_i_stb.next = False
        print("Output: %s" % test_cache_o_dat)

    return clk_driver, drive_test, drive_comb, test_ram, test_cache

inst = Top()
inst.run_sim(20 * 1600)