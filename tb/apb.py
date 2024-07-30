
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
Testbench of the apbi2c controller - APB Transaction and Agent 
(Driver + Monitor)

"""

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly
from cocotb_bus.drivers import BusDriver
from cocotb_bus.monitors import BusMonitor

from cocotb_coverage.crv import Randomized

#APB Transaction object
class APBTransaction(Randomized):

    def __init__(self, address, data=0, write=False, delay=1):
        Randomized.__init__(self)
        self.addr = address
        self.data = data
        self.write = write
        self.delay = delay
        
        #delay as a random variable
        self.add_rand("delay", range(0,10))

#APB Interface Logic
class APBSlave(BusDriver, BusMonitor):
    '''
    APB Slave
    '''
    _signals = [
        "PWRITE", "PSELx", "PENABLE", "PADDR",  "PWDATA", 
        "PREADY",  "PRDATA"
        ]

    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)
        BusMonitor.__init__(self, entity, name, clock)
        self.clock = clock
        self.bus.PWRITE.setimmediatevalue(0)
        self.bus.PSELx.setimmediatevalue(0)
        self.bus.PENABLE.setimmediatevalue(0)
        self.bus.PADDR.setimmediatevalue(0)
        self.bus.PWDATA.setimmediatevalue(0)
        
    #APB DRIVER: Transaction Executed by Master
    async def send(self, transaction):
        rval = 0
        await RisingEdge(self.clock)
        self.bus.PADDR.value = transaction.addr
        self.bus.PWDATA.value = transaction.data
        self.bus.PSELx.value = 1
        self.bus.PWRITE.value = 1 if transaction.write else 0
        await RisingEdge(self.clock)
        self.bus.PENABLE.value = 1
        while True:
            await ReadOnly()
            if (self.bus.PREADY == 1):
                rval = self.bus.PRDATA
                break
            await RisingEdge(self.clock)
        await RisingEdge(self.clock)
        self.bus.PADDR.value = 0
        self.bus.PWDATA.value = 0
        self.bus.PSELx.value = 0
        self.bus.PWRITE.value = 0
        self.bus.PENABLE.value = 0
        for i in range(transaction.delay):
            await RisingEdge(self.clock)
        return rval

    #APB MONITOR: Observe interface to monitor all transactions
    async def _monitor_recv(self):
        delay = 0
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()
            if (self.bus.PENABLE == 1) & (self.bus.PREADY == 1):
                data = self.bus.PWDATA if self.bus.PWRITE \
                  else self.bus.PRDATA
                xaction = APBTransaction(
                  self.bus.PADDR, data, self.bus.PWRITE == 1, delay
                )
                delay = 0
                self._recv(xaction)
            else:
                delay = delay + 1
