from myhdl import *

t_State = enum("IDLE", "LERP1", "LERP2")

@block
def TexSampler(i_rstn, i_clk, i_stb, i_st, i_w, i_h, i_clmp_s, i_clmp_t, o_dat, o_ack,
               o_tc_stb, o_tc_smp, i_tc_dat, i_tc_ack):
    """
    Sampler which takes as input 24.12 fixed point ST coordinates and texture width/height and produces a sample position which can be routed to a TexCache,
    as well as taking sampled data input from said TexCache and performing bilinear filtering on the result

    - i_stb: Input request signal
    - i_st: Input texture coordinates (S,T) 24.12 fixed point
    - i_w: log2 of texture width
    - i_h: log2 of texture height
    - i_clmp_s: Clamp S
    - i_clmp_t: Clamp T
    - o_dat: Output sampled color
    - o_ack: Output valid signal
    
    - o_tc_stb: Output request signal to backing TexCache
    - o_tc_smp: Output sample coordinate to backing TexCache
    - i_tc_dat: Input sample data from backing TexCache
    - i_tc_ack: Input ack signal from backing TexCache
    """

    _state = Signal(t_State.IDLE)

    _samples = [Signal(intbv(0)[32:]) for _ in range(4)]

    _px = Signal(intbv(0)[32:].signed())
    _py = Signal(intbv(0)[32:].signed())
    
    _dx0_r = Signal(intbv(0)[32:].signed())
    _dx0_g = Signal(intbv(0)[32:].signed())
    _dx0_b = Signal(intbv(0)[32:].signed())
    _dx0_a = Signal(intbv(0)[32:].signed())
    
    _dx1_r = Signal(intbv(0)[32:].signed())
    _dx1_g = Signal(intbv(0)[32:].signed())
    _dx1_b = Signal(intbv(0)[32:].signed())
    _dx1_a = Signal(intbv(0)[32:].signed())
    
    _dy_r = Signal(intbv(0)[32:].signed())
    _dy_g = Signal(intbv(0)[32:].signed())
    _dy_b = Signal(intbv(0)[32:].signed())
    _dy_a = Signal(intbv(0)[32:].signed())

    def read_req():
        _samples[0].next = i_tc_dat[0]
        _samples[1].next = i_tc_dat[1]
        _samples[2].next = i_tc_dat[2]
        _samples[3].next = i_tc_dat[3]
        
        _px.next = i_st[0] << i_w
        _py.next = i_st[1] << i_h

        _dx0_r.next = concat(intbv(0)[24:0], i_tc_dat[1][8:0])      - concat(intbv(0)[24:0], i_tc_dat[0][8:0])
        _dx0_g.next = concat(intbv(0)[24:0], i_tc_dat[1][16:8])     - concat(intbv(0)[24:0], i_tc_dat[0][16:8])
        _dx0_b.next = concat(intbv(0)[24:0], i_tc_dat[1][24:16])    - concat(intbv(0)[24:0], i_tc_dat[0][24:16])
        _dx0_a.next = concat(intbv(0)[24:0], i_tc_dat[1][32:24])    - concat(intbv(0)[24:0], i_tc_dat[0][32:24])
        _dx1_r.next = concat(intbv(0)[24:0], i_tc_dat[3][8:0])      - concat(intbv(0)[24:0], i_tc_dat[2][8:0])
        _dx1_g.next = concat(intbv(0)[24:0], i_tc_dat[3][16:8])     - concat(intbv(0)[24:0], i_tc_dat[2][16:8])
        _dx1_b.next = concat(intbv(0)[24:0], i_tc_dat[3][24:16])    - concat(intbv(0)[24:0], i_tc_dat[2][24:16])
        _dx1_a.next = concat(intbv(0)[24:0], i_tc_dat[3][32:24])    - concat(intbv(0)[24:0], i_tc_dat[2][32:24])

    @always(i_clk.posedge, i_rstn)
    def clk_logic():
        if i_rstn == 0:
            _state.next = t_State.IDLE
        elif _state == t_State.IDLE:
            if i_stb and i_tc_ack:
                read_req()
                _state.next = t_State.LERP1
        elif _state == t_State.LERP1:
            dx0r_next = _samples[0][8:0] + ((_dx0_r * _px[12:0]) >> 12)
            dx0g_next = _samples[0][16:8] + ((_dx0_g * _px[12:0]) >> 12)
            dx0b_next = _samples[0][24:16] + ((_dx0_b * _px[12:0]) >> 12)
            dx0a_next = _samples[0][32:24] + ((_dx0_a * _px[12:0]) >> 12)
            dx1r_next = _samples[2][8:0] + ((_dx1_r * _px[12:0]) >> 12)
            dx1g_next = _samples[2][16:8] + ((_dx1_g * _px[12:0]) >> 12)
            dx1b_next = _samples[2][24:16] + ((_dx1_b * _px[12:0]) >> 12)
            dx1a_next = _samples[2][32:24] + ((_dx1_a * _px[12:0]) >> 12)
            _dx0_r.next = dx0r_next
            _dx0_g.next = dx0g_next
            _dx0_b.next = dx0b_next
            _dx0_a.next = dx0a_next
            _dy_r.next = dx1r_next - dx0r_next
            _dy_g.next = dx1g_next - dx0g_next
            _dy_b.next = dx1b_next - dx0b_next
            _dy_a.next = dx1a_next - dx0a_next
            _state.next = t_State.LERP2
        elif _state == t_State.LERP2:
            if i_stb and i_tc_ack:
                read_req()
                _state.next = t_State.LERP1
            else:
                _state.next = t_State.IDLE

    @always_comb
    def comb_logic():
        x = i_st[0] << i_w
        y = i_st[1] << i_h

        o_tc_smp[0].next = x[32:12]
        o_tc_smp[1].next = y[32:12]

        r = intbv(_dx0_r + ((_dy_r * _py[12:0]) >> 12))[8:0]
        g = intbv(_dx0_g + ((_dy_g * _py[12:0]) >> 12))[8:0]
        b = intbv(_dx0_b + ((_dy_b * _py[12:0]) >> 12))[8:0]
        a = intbv(_dx0_a + ((_dy_a * _py[12:0]) >> 12))[8:0]
        o_dat.next = concat(a, b, g, r)

        o_ack.next = i_stb and (_state == t_State.LERP2)
        o_tc_stb.next = i_stb and (_state == t_State.IDLE or _state == t_State.LERP2)

    return clk_logic, comb_logic