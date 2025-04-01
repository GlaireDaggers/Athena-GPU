from myhdl import *

@block
def BusArbiter(i_rstn, i_clk, i_adr, i_dat, o_dat, i_we, i_stb, o_ack,
               o_mem_adr, o_mem_dat, i_mem_dat, o_mem_we, o_mem_stb, i_mem_ack,
               NUM_PORTS=4):

    """
    Super simple priority-based bus arbiter. Note: Makes no attempt to prevent clients from hogging the bus

    - i_rstn: Reset signal
    - i_clk: Clock signal

    - i_adr: Input address lines [NUM_PORTS]
    - i_dat: Input data lines [NUM_PORTS]
    - o_dat: Output data line
    - i_we: Input write enable lines [NUM_PORTS]
    - i_stb: Input request transaction lines [NUM_PORTS]
    - o_ack: Output transaction acknowledge lines [NUM_PORTS]

    - o_mem_adr: Output address line to backing memory
    - o_mem_dat: Output data line to backing memory
    - i_mem_dat: Input data line from backing memory
    - o_mem_we: Output write enable signal to backing memory
    - o_mem_stb: Output request transaction signal to backing memory
    - i_mem_ack: Input transaction acknowledge signal from backing memory
    """

    _active_grant = Signal(intbv(0)[8:0])
    _is_active = Signal(bool(0))

    @always(i_clk.posedge, i_rstn)
    def clk_logic():
        if i_rstn == 0:
            _is_active.next = False
        elif _is_active == False:
            # first client in the list who requests a transaction is granted access until the request is acknowledged
            for i in range(NUM_PORTS):
                if i_stb[i]:
                    _active_grant.next = i
                    _is_active.next = True
                    break
        elif _is_active == True:
            # if request is acknowledged, release grant
            if i_mem_ack:
                _is_active.next = False

    @always_comb
    def comb_logic():
        o_mem_adr.next = i_adr[_active_grant]
        o_mem_dat.next = i_dat[_active_grant]
        o_mem_we.next = i_we[_active_grant]
        o_mem_stb.next = i_stb[_active_grant] and _is_active
        o_dat.next = i_mem_dat
        for i in range(NUM_PORTS):
            o_ack[i].next = i_mem_ack and _active_grant == i

    return clk_logic, comb_logic