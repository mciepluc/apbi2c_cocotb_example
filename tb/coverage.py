
'''Copyright (c) 2019, Marek Cieplucha, https://github.com/mciepluc
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

from cocotb_coverage.coverage import *

#Functional coverage of the tested controller - sort of a verification plan

#APB functional coverage: READ/WRITE, random delay and all addresses 
#from the register space
#also cross of the delay with R/W
APBCoverage = coverage_section(
  CoverPoint("top.apb.delay", 
    xf = lambda xaction : xaction.delay, 
    rel = lambda _val, _range : _range[0] < _val < _range[1],
    bins = [(0,3), (4,7), (8,15)],
    bins_labels = ["small", "medium", "big"]
  ),
  CoverPoint("top.apb.addr",  
    xf = lambda xaction : xaction.addr, bins = [0,4,8,12],
    bins_labels = ["write_access", "read_access", "i2c_reg_config", 
      "i2c_reg_timeout"]
  ),
  CoverPoint("top.apb.write", 
    xf = lambda xaction : xaction.write, bins = [True, False]
  ),
  CoverCross("top.apb.writeXdelay", 
    items = ["top.apb.delay", "top.apb.write"]
  )
)

#I2C Functional Coverage - just check if different data processed
I2CCoverage = coverage_section(
  CoverPoint("top.i2c.data", 
    xf = lambda xaction : xaction.data >> 24, 
    bins = list(range(0,255))
  ),
)

#Operations coverage: READ/WRITE, number of words transmitted and clock divider
#cross of the above as a main verification goal
OperationsCoverage = coverage_section(
  CoverPoint("top.op.direction",  
    xf = lambda operation, ok : operation.direction, 
    bins = ['read', 'write']
  ),
  CoverPoint("top.op.repeat",  
    xf = lambda operation, ok : operation.repeat, 
    rel = lambda _val, _range : _range[0] <= _val <= _range[1],
    bins = [(1,3), (4,7), (8,11), (12,15), (16,23), (24,31)]
  ),  
  CoverPoint("top.op.divider",  
    xf = lambda operation, ok : operation.divider, 
    rel = lambda _val, _range : _range[0] <= _val <= _range[1],
    bins = [(1,3), (4,7), (8,11), (12,15), (16,23), (24,31)]
  ),
  CoverCross("top.op.cross", 
    items = ["top.op.direction", "top.op.repeat", "top.op.divider"]
  )
)

#Operations order coverage: check if performed two operations
#in a defined order e.g. read then write
OperationsOrderCoverage = coverage_section(
  CoverPoint("top.op.direction_order",  
    xf = lambda prev_operation, operation : 
      (prev_operation.direction, operation.direction),
    bins = [("read", "read"), ("read", "write"), 
      ("write", "read"), ("write", "write")
    ]
  ),
  CoverPoint("top.op.repeat_order",  
    xf = lambda prev_operation, operation : 
      prev_operation.repeat - operation.repeat,
    rel = lambda _val, _range : _range[0] <= _val <= _range[1],
    bins = [(0, 0), (-7, -1), (1, 7)]
  )
)
