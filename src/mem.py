from myhdl import block, always, always_comb, Signal, intbv

@block
def RAM(o_data, i_data, i_addr, i_we, i_clk, WIDTH=8, DEPTH=128, ID="mem"):
    _mem = [Signal(intbv(0)[WIDTH:]) for _ in range(DEPTH)]

    @always(i_clk.posedge)
    def write():
        if i_we:
            # print("%s WRITE: %s -> %s" % (ID, i_data, i_addr))
            _mem[i_addr].next = i_data

    @always_comb
    def read():
        o_data.next = _mem[i_addr]

    return write, read

@block
def ROM(o_data, i_addr, CONTENT):
    @always_comb
    def read():
        o_data.next = CONTENT[int(i_addr)]

    return read