from myhdl import *

t_State = enum("IDLE", "LERP1", "LERP2")

@block
def TexSampler(i_rstn, i_clk, i_stb, i_st, i_ddx, i_ddy, i_w, i_h, i_clmp_s, i_clmp_t, i_flt, i_mip, o_dat, o_ack,
               o_tc_stb, o_tc_smp, o_tc_mip, i_tc_dat, i_tc_ack):
    """
    Sampler which takes as input 24.12 fixed point ST coordinates and texture width/height and produces a sample position which can be routed to a TexCache,
    as well as taking sampled data input from said TexCache and performing bilinear filtering on the result

    - i_stb: Input request signal
    - i_st: Input texture coordinates (S,T) 24.12 fixed point
    - i_ddx: Input change of (S, T) wrt X (24.12 fixed point)
    - i_ddy: Input change of (S, T) wrt Y (24.12 fixed point)
    - i_w: log2 of texture width
    - i_h: log2 of texture height
    - i_clmp_s: Clamp S
    - i_clmp_t: Clamp T
    - i_flt: Input enable filter signal
    - i_mip: Input enable mip signal
    - o_dat: Output sampled color
    - o_ack: Output valid signal
    
    - o_tc_stb: Output request signal to backing TexCache
    - o_tc_smp: Output sample coordinate to backing TexCache
    - o_tc_mip: Output mip level to backing TexCache
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

    def clamp_coord(v, vmin, vmax):
        if v < vmin:
            return vmin
        elif v >= vmax:
            return vmax
        return v

    def read_req():
        _samples[0].next = i_tc_dat[0]
        _samples[1].next = i_tc_dat[1]
        _samples[2].next = i_tc_dat[2]
        _samples[3].next = i_tc_dat[3]
        
        _dx0_r.next = concat(intbv(0)[24:0], i_tc_dat[1][8:0])      - concat(intbv(0)[24:0], i_tc_dat[0][8:0])
        _dx0_g.next = concat(intbv(0)[24:0], i_tc_dat[1][16:8])     - concat(intbv(0)[24:0], i_tc_dat[0][16:8])
        _dx0_b.next = concat(intbv(0)[24:0], i_tc_dat[1][24:16])    - concat(intbv(0)[24:0], i_tc_dat[0][24:16])
        _dx0_a.next = concat(intbv(0)[24:0], i_tc_dat[1][32:24])    - concat(intbv(0)[24:0], i_tc_dat[0][32:24])
        _dx1_r.next = concat(intbv(0)[24:0], i_tc_dat[3][8:0])      - concat(intbv(0)[24:0], i_tc_dat[2][8:0])
        _dx1_g.next = concat(intbv(0)[24:0], i_tc_dat[3][16:8])     - concat(intbv(0)[24:0], i_tc_dat[2][16:8])
        _dx1_b.next = concat(intbv(0)[24:0], i_tc_dat[3][24:16])    - concat(intbv(0)[24:0], i_tc_dat[2][24:16])
        _dx1_a.next = concat(intbv(0)[24:0], i_tc_dat[3][32:24])    - concat(intbv(0)[24:0], i_tc_dat[2][32:24])

        if i_flt:
            _state.next = t_State.LERP1
        else:
            _state.next = t_State.IDLE

    @always(i_clk.posedge, i_rstn)
    def clk_logic():
        if i_rstn == 0:
            _state.next = t_State.IDLE
        elif _state == t_State.IDLE:
            if i_stb and i_tc_ack:
                read_req()
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
            _state.next = t_State.IDLE

    def log2_int(a, BITLEN=32):
        for i in range(BITLEN - 1, -1, -1):
            if a[i]:
                return i
        return 0

    @always_comb
    def comb_logic():
        # calculate mip level from ddx/ddy
        dsdx = i_ddx[0] << i_w
        dtdx = i_ddx[1] << i_w
        dsdy = i_ddy[0] << i_h
        dtdy = i_ddy[1] << i_h

        ddx = ((dsdx * dsdx) >> 12) + ((dtdx * dtdx) >> 12)
        ddy = ((dsdy * dsdy) >> 12) + ((dtdy * dtdy) >> 12)

        # NOTE: smallest possible size for a texture is 4x4 since that's a single block size
        # so for a 512x512 texture, the size is given to the hardware as log2(512) = 9, and that will have 8 possible mip levels:
        # 512, 256, 128, 64, 32, 16, 8, 4
        # so max mip level is 7 (basically we subtract 2 to ignore the last two "mips" of 2x2 and 1x1 since those aren't possible)
        maxmip_w = i_w - 2 if i_w >= 2 else 0
        maxmip_h = i_h - 2 if i_h >= 2 else 0
        maxmip = min(maxmip_w, maxmip_h)
        mip = min(log2_int(intbv(max(ddx, ddy))[32:12], BITLEN=20) >> 1, maxmip) if i_mip else 0

        o_tc_mip.next = mip

        mipw = i_w >> mip
        miph = i_h >> mip

        maxw = (1 << mipw) - 1
        maxh = (1 << miph) - 1

        # note: half texel bias
        x = (i_st[0] << mipw) - 2048
        y = (i_st[1] << miph) - 2048

        sx = clamp_coord(x, 0, maxw << 12) if i_clmp_s else x
        sy = clamp_coord(y, 0, maxh << 12) if i_clmp_t else y

        _px.next = sx
        _py.next = sy

        o_tc_smp[0].next = (sx >> 12) & maxw
        o_tc_smp[1].next = (sy >> 12) & maxh

        if i_flt:
            r = intbv(_dx0_r + ((_dy_r * _py[12:0]) >> 12))[8:0]
            g = intbv(_dx0_g + ((_dy_g * _py[12:0]) >> 12))[8:0]
            b = intbv(_dx0_b + ((_dy_b * _py[12:0]) >> 12))[8:0]
            a = intbv(_dx0_a + ((_dy_a * _py[12:0]) >> 12))[8:0]
            o_dat.next = concat(a, b, g, r)
            o_ack.next = i_stb and _state == t_State.LERP2
        else:
            o_dat.next = i_tc_dat[0]
            o_ack.next = i_stb and i_tc_ack

        o_tc_stb.next = i_stb and (_state == t_State.IDLE or _state == t_State.LERP2)

    return clk_logic, comb_logic