import cocotb
from cocotb import coverage

APBCoverage = cocotb.coverage.coverageSection(
  cocotb.coverage.CoverPoint("apb.delay", 
    xf = lambda xaction : xaction.delay, 
    rel = lambda _val, _range : _range[0] < _val < _range[1],
    bins = [(0,5), (5,10), (10,15)]
  ),
  cocotb.coverage.CoverPoint("apb.addr",  xf = lambda xaction : xaction.addr, bins = [0,4,8,12]),
  cocotb.coverage.CoverPoint("apb.write", xf = lambda xaction : xaction.write, bins = [True, False]),
  cocotb.coverage.CoverCross("apb.writeXdelay", items = ["apb.delay", "apb.write"])
)

I2CCoverage = cocotb.coverage.coverageSection(
  cocotb.coverage.CoverPoint("i2c.data", 
    xf = lambda xaction : xaction.data, 
    rel = lambda _val, _range : _range[0] < _val < _range[1],
    bins = [(0,0xFF), (0x100, 0xFFFF), (0x10000,0xFFFFFFFF)]
  ),
)
