
'''Copyright (c) 2017, Marek Cieplucha, https://github.com/mciepluc
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met (The BSD 2-Clause 
License):

1. Redistributions of source code must retain the above copyright notice, 
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, 
this list of conditions and the following disclaimer in the documentation and/or 
other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

"""
Testbench of the apbi2c controller - functional coverage

"""

import cocotb
from cocotb import coverage

#Functional coverage of the tested controller - sort of a verification plan

#APB functional coverage: READ/WRITE, random delay and all addresses from the register space
#also cross of the delay with R/W
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

#I2C Functional Coverage - just check if different data processed
I2CCoverage = cocotb.coverage.coverageSection(
  cocotb.coverage.CoverPoint("i2c.data", 
    xf = lambda xaction : xaction.data, 
    rel = lambda _val, _range : _range[0] <= _val <= _range[1],
    bins = [(0,0xFFFF), (0x10000, 0xFFFFFF), (0x1000000,0xFFFFFFFF)]
  ),
)

#Operations coverage: READ/WRITE, number of words transmitted and clock divider
#cross of the above as a main verification goal
OperationsCoverage = cocotb.coverage.coverageSection(
  cocotb.coverage.CoverPoint("op.direction",  
    xf = lambda direction, repeat, divider, ok : direction, 
    bins = ['read', 'write']
  ),
  cocotb.coverage.CoverPoint("op.repeat",  
    xf = lambda direction, repeat, divider, ok : repeat, 
    rel = lambda _val, _range : _range[0] <= _val <= _range[1],
    bins = [(1,3), (4,7), (8,15), (16,31)]
  ),  
  cocotb.coverage.CoverPoint("op.divider",  
    xf = lambda direction, repeat, divider, ok : divider, 
    rel = lambda _val, _range : _range[0] <= _val <= _range[1],
    bins = [(1,3), (4,7), (8,15), (16,31)]
  ),
  cocotb.coverage.CoverCross("op.cross", items = ["op.direction", "op.repeat", "op.divider"])
)

#Operations order coverage: check if performed two operations
#in a defined order e.g. read then write
OperationsOrderCoverage = cocotb.coverage.CoverPoint("op.order",  
    xf = lambda prev_direction, direction : (prev_direction, direction),
    bins = [("read", "read"), ("read", "write"), ("write", "read"), ("write", "write")]
  )
