from myhdl import block, delay, instance

@block
def ClkDriver(o_clk, PERIOD=20):
    lowTime = int(PERIOD / 2)
    highTime = PERIOD - lowTime

    @instance
    def drive_clk():
        while True:
            yield delay(lowTime)
            o_clk.next = 1
            yield delay(highTime)
            o_clk.next = 0

    return drive_clk