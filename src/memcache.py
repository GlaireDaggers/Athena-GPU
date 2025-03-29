from myhdl import *

t_State = enum("IDLE", "FILL")

@block
def MemCache(i_rstn, i_clk, i_adr, o_dat, i_stb, o_ack,
             o_mem_adr, i_mem_dat, o_mem_stb, i_mem_ack,
             WIDTH=8, ADRBITS=32, IDXBITS=7):
    DEPTH = 1 << IDXBITS
    TAGBITS = ADRBITS - IDXBITS

    """
    A basic read-only memory cache

    - i_rst: Reset signal
    - i_clk: Clock signal
    
    - i_adr: Input read address
    - o_dat: Output read data
    - i_stb: Request transaction signal
    - o_ack: Output data valid signal

    - o_mem_adr: Output read address to backing memory
    - i_mem_dat: Input read data from backing memory
    - o_mem_stb: Output request transaction signal to backing memory
    - i_mem_ack: Input data valid signal from backing memory
    
    - WIDTH: width of data in bits
    - ADRBITS: width of address line in bits
    - IDXBITS: portion of address line dedicated to index bits (controls size of cache)
    """

    _cachemem = [Signal(intbv(0)[WIDTH:]) for _ in range(DEPTH)]
    _tag = Signal(intbv(0)[TAGBITS:])
    _valid = Signal(bool(0))
    _state = Signal(t_State.IDLE)
    _filladr = Signal(intbv(0)[TAGBITS:])
    _filloffs = Signal(intbv(0)[IDXBITS:])

    @always(i_clk.posedge, i_rstn)
    def reset_and_fill():
        if i_rstn == 0:
            _valid.next = False
            _state.next = t_State.IDLE
        elif _state == t_State.IDLE:
            # if requested address is not in cache, switch to FILL state
            if i_stb and (not _valid or _tag != i_adr[ADRBITS:IDXBITS]):
                print("Cache miss (input address: %s, tag: %s, valid: %s)" % (i_adr, _tag, _valid))
                _state.next = t_State.FILL
                _filloffs.next = 0
                _filladr.next = i_adr[ADRBITS:IDXBITS]
        elif _state == t_State.FILL:
            # if backing memory acks request, fill spot and increment
            # when cache is full, set tag & valid and switch back to IDLE state
            if i_mem_ack:
                print("Fill cache (offs: %d, addr: %s, data: %s)" % (_filloffs, o_mem_adr, i_mem_dat))
                _cachemem[_filloffs].next = i_mem_dat
                if _filloffs == (1 << IDXBITS) - 1:
                    _tag.next = _filladr
                    _valid.next = True
                    _state.next = t_State.IDLE
                    print("Cache filled")
                else:
                    _filloffs.next = _filloffs + 1

    @always_comb
    def access():
        o_ack.next = _tag == i_adr[ADRBITS:IDXBITS] and _valid and i_stb
        o_dat.next = _cachemem[i_adr[IDXBITS:]]
        o_mem_adr.next = concat(_filladr, _filloffs)
        o_mem_stb.next = _state == t_State.FILL

    return reset_and_fill, access