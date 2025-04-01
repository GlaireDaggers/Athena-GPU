from myhdl import *

t_State = enum("WAITING", "SETUP1", "SETUP2", "SETUP3", "SETUP4", "RASTERLOOP", "TEX0", "TEX1", "TEX2", "TEX3")

@block
def TriRaster(i_rst, i_clk, i_v0, i_v1, i_v2,
              i_col_init, i_col_dx, i_col_dy,
              i_1ow_init, i_1ow_dx, i_1ow_dy,
              i_sow_init, i_sow_dx, i_sow_dy,
              i_tow_init, i_tow_dx, i_tow_dy,
              i_zow_init, i_zow_dx, i_zow_dy,
              i_tex_en, i_dtest_en, i_dcmp,
              i_stb, o_busy, o_wr_en_rgb, o_wr_data_rgb, o_wr_en_d, o_wr_data_d, o_wr_pos,
              i_rd_data_rgb, i_rd_data_d,
              o_smp_stb, o_smp_st, i_smp_dat, i_smp_ack,
              DIM=32):
    """
    Triangle rasterizer

    - i_rst: Reset signal
    - i_clk: Clock signal
    - i_v0: triangle vertex 0 x/y
    - i_v1: triangle vertex 1 x/y
    - i_v2: triangle vertex 2 x/y
    - i_col_init: starting color (at top left corner of triangle bounds) - Q8.12 fixed point
    - i_col_dx: color increment wrt x - Q8.12 fixed point
    - i_col_dy: color increment wrt y - Q8.12 fixed point
    - i_1ow_init: starting 1/w (at top left corner of triangle bounds) - Q12.12 fixed point
    - i_1ow_dx: 1/w increment wrt x - Q12.12 fixed point
    - i_1ow_dy: 1/w increment wrt y - Q12.12 fixed point
    - i_sow_init: starting s/w (at top left corner of triangle bounds) - Q12.12 fixed point
    - i_sow_dx: s/w increment wrt x - Q12.12 fixed point
    - i_sow_dy: s/w increment wrt y - Q12.12 fixed point
    - i_tow_init: starting t/w (at top left corner of triangle bounds) - Q12.12 fixed point
    - i_tow_dx: t/w increment wrt x - Q12.12 fixed point
    - i_tow_dy: t/w increment wrt y - Q12.12 fixed point
    - i_zow_init: starting z/w (at top left corner of triangle bounds) - Q12.12 fixed point
    - i_zow_dx: z/w increment wrt x - Q12.12 fixed point
    - i_zow_dy: z/w increment wrt y - Q12.12 fixed point
    - i_tex_en: Enable texturing
    - i_dtest_en: Enable depth test
    - i_dcmp: Depth compare mode (0 = never, 1 = always, 2 = equal, 3 = not-equal, 4 = less, 5 = greater, 6 = less-or-equal, 7 = greater-or-equal)
    - i_stb: Input draw triangle request signal
    - o_busy: 1 if busy, 0 if idle
    - o_wr_en_rgb: for each pixel in cluster, 1 if output pixel color is valid, 0 otherwise
    - o_wr_data_rgb: Output pixel cluster colors
    - o_wr_en_ds: for each pixel in cluster, 1 if output pixel depth is valid, 0 otherwise
    - o_wr_data_d: Output pixel cluster depth values
    - o_wr_pos: Output pixel cluster x/y
    - i_rd_data_rgb: Input pixel cluster colors
    - i_rd_data_d: Input pixel cluster depth values
    - o_smp_stb: Output request transaction signal to TexSampler unit
    - o_smp_st: Output ST coordinates to TexSampler unit
    - i_smp_dat: Input texture sample from TexSampler unit
    - i_smp_ack: Input request acknowledge signal from TexSampler unit
    
    - DIM: width/height of render area
    """

    _state = Signal(t_State.WAITING)
    _v0 = [Signal(intbv(0)[32:0].signed()) for _ in range(2)]
    _v1 = [Signal(intbv(0)[32:0].signed()) for _ in range(2)]
    _v2 = [Signal(intbv(0)[32:0].signed()) for _ in range(2)]
    _bmin = [Signal(intbv(0)[32:0].signed()) for _ in range(2)]
    _bmax = [Signal(intbv(0)[32:0].signed()) for _ in range(2)]
    _offs = [Signal(intbv(0)[32:0].signed()) for _ in range(2)]
    _a01 = Signal(intbv(0)[32:0].signed())
    _a12 = Signal(intbv(0)[32:0].signed())
    _a20 = Signal(intbv(0)[32:0].signed())
    _b01 = Signal(intbv(0)[32:0].signed())
    _b12 = Signal(intbv(0)[32:0].signed())
    _b20 = Signal(intbv(0)[32:0].signed())
    _bias0 = Signal(intbv(0)[32:0].signed())
    _bias1 = Signal(intbv(0)[32:0].signed())
    _bias2 = Signal(intbv(0)[32:0].signed())
    _w0_row = Signal(intbv(0)[32:0].signed())
    _w1_row = Signal(intbv(0)[32:0].signed())
    _w2_row = Signal(intbv(0)[32:0].signed())
    _w0 = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]
    _w1 = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]
    _w2 = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]
    _p = [Signal(intbv(0)[32:0]) for _ in range(2)]

    _col_row = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]
    _col_dx = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]
    _col_dy = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]
    _col = [[Signal(intbv(0)[32:0].signed()) for _ in range(4)] for _ in range(4)]

    _1ow_row = Signal(intbv(0)[32:0].signed())
    _1ow_dx = Signal(intbv(0)[32:0].signed())
    _1ow_dy = Signal(intbv(0)[32:0].signed())
    _1ow = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]

    _sow_row = Signal(intbv(0)[32:0].signed())
    _sow_dx = Signal(intbv(0)[32:0].signed())
    _sow_dy = Signal(intbv(0)[32:0].signed())
    _sow = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]

    _tow_row = Signal(intbv(0)[32:0].signed())
    _tow_dx = Signal(intbv(0)[32:0].signed())
    _tow_dy = Signal(intbv(0)[32:0].signed())
    _tow = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]

    _zow_row = Signal(intbv(0)[32:0].signed())
    _zow_dx = Signal(intbv(0)[32:0].signed())
    _zow_dy = Signal(intbv(0)[32:0].signed())
    _zow = [Signal(intbv(0)[32:0].signed()) for _ in range(4)]

    _tex_col = [Signal(intbv(0)[32:0]) for _ in range(4)]

    _sample_valid = [Signal(bool(0)) for _ in range(4)]
    _depth_test = [Signal(bool(0)) for _ in range(4)]

    def isTopLeft(a, b):
        return (a[1] == b[1] and b[0] > a[0]) or (b[1] > a[1])

    def min2(a, b):
        return a if a < b else b
    
    def max2(a, b):
        return a if a > b else b
    
    def orient2D(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        
    def depth_test():
        if i_dcmp == 0:
            return [not i_dtest_en for _ in range(4)]
        elif i_dcmp == 1:
            return [True for _ in range(4)]
        elif i_dcmp == 2:
            return [(not i_dtest_en or _zow[i] == i_rd_data_d[i]) for i in range(4)]
        elif i_dcmp == 3:
            return [(not i_dtest_en or _zow[i] != i_rd_data_d[i]) for i in range(4)]
        elif i_dcmp == 4:
            return [(not i_dtest_en or _zow[i] < i_rd_data_d[i]) for i in range(4)]
        elif i_dcmp == 5:
            return [(not i_dtest_en or _zow[i] > i_rd_data_d[i]) for i in range(4)]
        elif i_dcmp == 6:
            return [(not i_dtest_en or _zow[i] <= i_rd_data_d[i]) for i in range(4)]
        elif i_dcmp == 7:
            return [(not i_dtest_en or _zow[i] >= i_rd_data_d[i]) for i in range(4)]
        else:
            return [False for _ in range(4)]
    
    @always(i_clk.posedge, i_rst)
    def process():
        if i_rst == 0:
            _state.next = t_State.WAITING
        elif _state == t_State.WAITING:
            if i_stb:
                # capture triangle parameters
                _v0[0].next = i_v0[0]
                _v0[1].next = i_v0[1]
                _v1[0].next = i_v1[0]
                _v1[1].next = i_v1[1]
                _v2[0].next = i_v2[0]
                _v2[1].next = i_v2[1]
                for i in range(4):
                    _col_row[i].next = i_col_init[i]
                    _col_dx[i].next = i_col_dx[i]
                    _col_dy[i].next = i_col_dy[i]
                _1ow_row.next = i_1ow_init
                _1ow_dx.next = i_1ow_dx
                _1ow_dy.next = i_1ow_dy
                _sow_row.next = i_sow_init
                _sow_dx.next = i_sow_dx
                _sow_dy.next = i_sow_dy
                _tow_row.next = i_tow_init
                _tow_dx.next = i_tow_dx
                _tow_dy.next = i_tow_dy
                _zow_row.next = i_zow_init
                _zow_dx.next = i_zow_dx
                _zow_dy.next = i_zow_dy
                # begin calculating triangle bounds
                _bmin[0].next = min2(i_v0[0], i_v1[0])
                _bmin[1].next = min2(i_v0[1], i_v1[1])
                _bmax[0].next = max2(i_v0[0], i_v1[0])
                _bmax[1].next = max2(i_v0[1], i_v1[1])
                #
                _state.next = t_State.SETUP1
        elif _state == t_State.SETUP1:
            # finish calculating triangle bounds
            _bmin[0].next = min2(_bmin[0], _v2[0])
            _bmin[1].next = min2(_bmin[1], _v2[1])
            _bmax[0].next = max2(_bmax[0], _v2[0])
            _bmax[1].next = max2(_bmax[1], _v2[1])
            # compute step increment values for barycentric weights
            _a01.next = _v0[1] - _v1[1]
            _a12.next = _v1[1] - _v2[1]
            _a20.next = _v2[1] - _v0[1]
            _b01.next = _v1[0] - _v0[0]
            _b12.next = _v2[0] - _v1[0]
            _b20.next = _v0[0] - _v2[0]
            # bias for top/left fill rule
            _bias0.next = 0 if isTopLeft(_v1, _v2) else -1
            _bias1.next = 0 if isTopLeft(_v2, _v0) else -1
            _bias2.next = 0 if isTopLeft(_v0, _v1) else -1
            #
            _state.next = t_State.SETUP2
        elif _state == t_State.SETUP2:
            # if top left corner of triangle bounds is less than 0, then compute offset value (used to offset triangle attributes such as colors, UVs, etc)
            _offs[0].next = -_bmin[0] if _bmin[0] < 0 else 0
            _offs[1].next = -_bmin[1] if _bmin[1] < 0 else 0
            # clamp bounds to render area
            # NOTE: we draw a 2x2 cluster at a time, so we also divide bounds by 2 (adding 1 to _bmax so it rounds up instead of down)
            _bmin[0].next = max2(_bmin[0] >> 1, 0)
            _bmin[1].next = max2(_bmin[1] >> 1, 0)
            _bmax[0].next = min2((_bmax[0] + 1) >> 1, (DIM >> 1) - 1)
            _bmax[1].next = min2((_bmax[1] + 1) >> 1, (DIM >> 1) - 1)
            #
            _state.next = t_State.SETUP3
        elif _state == t_State.SETUP3:
            # offset triangle attribute iterators
            for i in range(4):
                _col_row[i].next = _col_row[i] + (_col_dx[i] * _offs[0]) + (_col_dy[i] * _offs[1])
            _1ow_row.next = _1ow_row + (_1ow_dx * _offs[0]) + (_1ow_dy * _offs[1])
            _sow_row.next = _sow_row + (_sow_dx * _offs[0]) + (_sow_dy * _offs[1])
            _tow_row.next = _tow_row + (_tow_dx * _offs[0]) + (_tow_dy * _offs[1])
            _zow_row.next = _zow_row + (_zow_dx * _offs[0]) + (_zow_dy * _offs[1])
            # store current position
            _p[0].next = _bmin[0]
            _p[1].next = _bmin[1]
            # compute row start values for barycentric weights
            new_w0_row = orient2D(i_v1, i_v2, _bmin) + _bias0
            new_w1_row = orient2D(i_v2, i_v0, _bmin) + _bias1
            new_w2_row = orient2D(i_v0, i_v1, _bmin) + _bias2
            _w0_row.next = new_w0_row
            _w1_row.next = new_w1_row
            _w2_row.next = new_w2_row
            # compute initial barycentric weights for 2x2 cluster
            _w0[0].next = new_w0_row
            _w1[0].next = new_w1_row
            _w2[0].next = new_w2_row
            _w0[1].next = new_w0_row + _a12
            _w1[1].next = new_w1_row + _a20
            _w2[1].next = new_w2_row + _a01
            _w0[2].next = new_w0_row + _b12
            _w1[2].next = new_w1_row + _b20
            _w2[2].next = new_w2_row + _b01
            _w0[3].next = new_w0_row + _a12 + _b12
            _w1[3].next = new_w1_row + _a20 + _b20
            _w2[3].next = new_w2_row + _a01 + _b01
            #
            _state.next = t_State.SETUP4
        elif _state == t_State.SETUP4:
            # compute initial color iterators for 2x2 cluster
            for i in range(4):
                _col[0][i].next = _col_row[i]
                _col[1][i].next = _col_row[i] + _col_dx[i]
                _col[2][i].next = _col_row[i] + _col_dy[i]
                _col[3][i].next = _col_row[i] + _col_dx[i] + _col_dy[i]
            # compute initial 1/w, s/w, t/w, and z/w iterators for 2x2 cluster
            _1ow[0].next = _1ow_row
            _1ow[1].next = _1ow_row + _1ow_dx
            _1ow[2].next = _1ow_row + _1ow_dy
            _1ow[3].next = _1ow_row + _1ow_dx + _1ow_dy
            _sow[0].next = _sow_row
            _sow[1].next = _sow_row + _sow_dx
            _sow[2].next = _sow_row + _sow_dy
            _sow[3].next = _sow_row + _sow_dx + _sow_dy
            _tow[0].next = _tow_row
            _tow[1].next = _tow_row + _tow_dx
            _tow[2].next = _tow_row + _tow_dy
            _tow[3].next = _tow_row + _tow_dx + _tow_dy
            _zow[0].next = _zow_row
            _zow[1].next = _zow_row + _zow_dx
            _zow[2].next = _zow_row + _zow_dy
            _zow[3].next = _zow_row + _zow_dx + _zow_dy
            #
            if i_tex_en:
                # if the computed bary weights lie outside the triangle, just skip texturing this cluster
                if (not _sample_valid[0]) and (not _sample_valid[1]) and (not _sample_valid[2]) and (not _sample_valid[3]):
                    _state.next = t_State.RASTERLOOP
                else:
                    _state.next = t_State.TEX0
            else:
                _state.next = t_State.RASTERLOOP
        elif _state == t_State.RASTERLOOP:
            if _p[0] == _bmax[0]:
                if _p[1] == _bmax[1]:
                    # finished
                    _state.next = t_State.WAITING
                else:
                    # new row, increment row start values & update current bary weights
                    next_w0_row = _w0_row + (_b12 << 1)
                    next_w1_row = _w1_row + (_b20 << 1)
                    next_w2_row = _w2_row + (_b01 << 1)
                    _w0_row.next = next_w0_row
                    _w1_row.next = next_w1_row
                    _w2_row.next = next_w2_row
                    # compute new barycentric weights for 2x2 cluster
                    _w0[0].next = next_w0_row
                    _w1[0].next = next_w1_row
                    _w2[0].next = next_w2_row
                    _w0[1].next = next_w0_row + _a12
                    _w1[1].next = next_w1_row + _a20
                    _w2[1].next = next_w2_row + _a01
                    _w0[2].next = next_w0_row + _b12
                    _w1[2].next = next_w1_row + _b20
                    _w2[2].next = next_w2_row + _b01
                    _w0[3].next = next_w0_row + _a12 + _b12
                    _w1[3].next = next_w1_row + _a20 + _b20
                    _w2[3].next = next_w2_row + _a01 + _b01
                    # increment color row start values & update current color iterators
                    for i in range(4):
                        next_col_row = _col_row[i] + (_col_dy[i] << 1)
                        _col_row[i].next = next_col_row
                        _col[0][i].next = next_col_row
                        _col[1][i].next = next_col_row + _col_dx[i]
                        _col[2][i].next = next_col_row + _col_dy[i]
                        _col[3][i].next = next_col_row + _col_dx[i] + _col_dy[i]
                    # increment 1/w, s/w, t/w, and z/w row start values & update current iterators
                    next_1ow_row = _1ow_row + (_1ow_dy << 1)
                    _1ow_row.next = next_1ow_row
                    _1ow[0].next = next_1ow_row
                    _1ow[1].next = next_1ow_row + _1ow_dx
                    _1ow[2].next = next_1ow_row + _1ow_dy
                    _1ow[3].next = next_1ow_row + _1ow_dx + _1ow_dy
                    #
                    next_sow_row = _sow_row + (_sow_dy << 1)
                    _sow_row.next = next_sow_row
                    _sow[0].next = next_sow_row
                    _sow[1].next = next_sow_row + _sow_dx
                    _sow[2].next = next_sow_row + _sow_dy
                    _sow[3].next = next_sow_row + _sow_dx + _sow_dy
                    #
                    next_tow_row = _tow_row + (_tow_dy << 1)
                    _tow_row.next = next_tow_row
                    _tow[0].next = next_tow_row
                    _tow[1].next = next_tow_row + _tow_dx
                    _tow[2].next = next_tow_row + _tow_dy
                    _tow[3].next = next_tow_row + _tow_dx + _tow_dy
                    #
                    next_zow_row = _zow_row + (_zow_dy << 1)
                    _zow_row.next = next_zow_row
                    _zow[0].next = next_zow_row
                    _zow[1].next = next_zow_row + _zow_dx
                    _zow[2].next = next_zow_row + _zow_dy
                    _zow[3].next = next_zow_row + _zow_dx + _zow_dy
                    # set position to next row
                    _p[0].next = _bmin[0]
                    _p[1].next = _p[1] + 1
                    # if texturing is enabled: switch to texturing state
                    if i_tex_en:
                        _state.next = t_State.TEX0
            else:
                # increment bary weights
                for i in range(4):
                    _w0[i].next = _w0[i] + (_a12 << 1)
                    _w1[i].next = _w1[i] + (_a20 << 1)
                    _w2[i].next = _w2[i] + (_a01 << 1)
                # increment color iterators
                for i in range(4):
                    for j in range(4):
                        _col[i][j].next = _col[i][j] + (_col_dx[j] << 1)
                # increment 1/w, s/w, t/w, and z/w iterators
                for i in range(4):
                    _1ow[i].next = _1ow[i] + (_1ow_dx << 1)
                    _sow[i].next = _sow[i] + (_sow_dx << 1)
                    _tow[i].next = _tow[i] + (_tow_dx << 1)
                    _zow[i].next = _zow[i] + (_zow_dx << 1)
                # increment position
                _p[0].next = _p[0] + 1
                # if texturing is enabled: switch to texturing state
                if i_tex_en:
                    _state.next = t_State.TEX0
        elif _state == t_State.TEX0:
            # actually if the computed bary weights lie outside the triangle, just skip texturing this cluster
            if (not _sample_valid[0] or not _depth_test[0]) and (not _sample_valid[1] or not _depth_test[1]) and (not _sample_valid[2] or not _depth_test[2]) and (not _sample_valid[3] or not _depth_test[3]):
                _state.next = t_State.RASTERLOOP
            elif i_smp_ack:
                _tex_col[0].next = i_smp_dat
                if _sample_valid[1] and _depth_test[1]:
                    _state.next = t_State.TEX1
                elif _sample_valid[2] and _depth_test[2]:
                    _state.next = t_State.TEX2
                elif _sample_valid[3] and _depth_test[3]:
                    _state.next = t_State.TEX3
                else:
                    _state.next = t_State.RASTERLOOP
        elif _state == t_State.TEX1:
            if i_smp_ack:
                _tex_col[1].next = i_smp_dat
                if _sample_valid[2] and _depth_test[2]:
                    _state.next = t_State.TEX2
                elif _sample_valid[3] and _depth_test[3]:
                    _state.next = t_State.TEX3
                else:
                    _state.next = t_State.RASTERLOOP
        elif _state == t_State.TEX2:
            if i_smp_ack:
                _tex_col[2].next = i_smp_dat
                _state.next = t_State.TEX3
                if _sample_valid[3] and _depth_test[3]:
                    _state.next = t_State.TEX3
                else:
                    _state.next = t_State.RASTERLOOP
        elif _state == t_State.TEX3:
            if i_smp_ack:
                _tex_col[3].next = i_smp_dat
                _state.next = t_State.RASTERLOOP

    @always_comb
    def process_comb():
        dtest = depth_test()
        smp_valid = [(_w0[i][31] | _w1[i][31] | _w2[i][31]) == 0 for i in range(4)]

        for i in range(4):
            _sample_valid[i].next = smp_valid[i]
            _depth_test[i].next = dtest[i]
            
            vr = _col[i][0][20:12]
            vg = _col[i][1][20:12]
            vb = _col[i][2][20:12]
            va = _col[i][3][20:12]
            tr = _tex_col[i][8:0]
            tg = _tex_col[i][16:8]
            tb = _tex_col[i][24:16]
            ta = _tex_col[i][32:24]
            if i_tex_en:
                cr = intbv((vr * tr) >> 8)[8:0]
                cg = intbv((vg * tg) >> 8)[8:0]
                cb = intbv((vb * tb) >> 8)[8:0]
                ca = intbv((va * ta) >> 8)[8:0]
                o_wr_data_rgb[i].next = concat(ca, cb, cg, cr)
            else:
                o_wr_data_rgb[i].next = concat(va, vb, vg, vr)

            o_wr_data_d[i].next = _zow[i]
            o_wr_en_rgb[i].next = o_wr_en_d[i].next = _state == t_State.RASTERLOOP and smp_valid[i] and dtest[i]

        o_smp_stb.next = _state == t_State.TEX0 or _state == t_State.TEX1 or _state == t_State.TEX2 or _state == t_State.TEX3

        if _state == t_State.TEX0:
            o_smp_st[0].next = (_sow[0] * _1ow[0]) >> 12
            o_smp_st[1].next = (_tow[0] * _1ow[0]) >> 12
        elif _state == t_State.TEX1:
            o_smp_st[0].next = (_sow[1] * _1ow[1]) >> 12
            o_smp_st[1].next = (_tow[1] * _1ow[1]) >> 12
        elif _state == t_State.TEX2:
            o_smp_st[0].next = (_sow[2] * _1ow[2]) >> 12
            o_smp_st[1].next = (_tow[2] * _1ow[2]) >> 12
        elif _state == t_State.TEX3:
            o_smp_st[0].next = (_sow[3] * _1ow[3]) >> 12
            o_smp_st[1].next = (_tow[3] * _1ow[3]) >> 12

        o_wr_pos[0].next = _p[0]
        o_wr_pos[1].next = _p[1]
        o_busy.next = _state != t_State.WAITING

    return process, process_comb