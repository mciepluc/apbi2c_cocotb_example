
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
Testbench of the apbi2c controller - I2C Transaction and Driver + Monitor

"""

import random
import cocotb
from cocotb.triggers import RisingEdge, ReadOnly
from cocotb.binary import BinaryValue
from cocotb.drivers import BusDriver
from cocotb.monitors import BusMonitor
from cocotb.decorators import coroutine

from cocotb_coverage.crv import Randomized

#I2C Transaction object
class I2CTransaction(Randomized):

    def __init__(self, data=0, write=False, divider = 1):
        Randomized.__init__(self)
        self.data = data
        self.write = write
        self.divider = divider
        
    def post_randomize(self):
        self.data = random.randint(0,0xFFFFFFFF)
    
    #overload (not)equlity operators - just compare data match
    def __ne__(self, other):
        return self.data != other.data
        
    def __eq__(self, other):
        return self.data == other.data

#I2C MONITOR - Observe interface to monitor all transactions
class I2CMonitor(BusMonitor):
    '''
    I2C Monitor
    '''
    _signals = ["SDA", "SCL"]

    def __init__(self, entity, name, clock):
        BusMonitor.__init__(self, entity, name, clock)
        self.clock = clock
        
    @cocotb.coroutine
    def _monitor_recv(self):
        started = False
        pre_started = False
        prev_scl = 1
        while True:
            yield RisingEdge(self.clock)
            yield ReadOnly()
            try:
                sda = 0 if self.bus.SDA == 'x' else int(self.bus.SDA)
            except ValueError:
                sda = 0
            if (self.bus.SCL == 1):
                #start bit
                if (not started) & (not pre_started) & (sda == 1):
                    pre_started = True
                elif (not started) & pre_started & (sda == 0):
                    started = True
                    pre_started = False
                    rdata = 0
                    data_cnt = 0
                    ack = 1
                #sample data at SCL
                elif started & (prev_scl == 0):
                    prev_scl = 1
                    if data_cnt == 32:
                        started = False
                        xaction = I2CTransaction(rdata, write=False)
                        self._recv(xaction)
                    elif (data_cnt%8 != 0) | ack:
                        ack = 0
                        rdata = rdata + (sda << data_cnt)
                        data_cnt += 1
                    else: #ack state
                        ack = 1
            elif started:
                prev_scl = 0
                
#I2C DRIVER: send I2C transaction via interface
class I2CDriver(BusDriver):
    '''
    I2C Driver
    '''
    _signals = ["SDA", "SCL"]

    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)
        self.clock = clock
        self.bus.SDA.setimmediatevalue(1)
        self.bus.SCL.setimmediatevalue(1)
        
    @cocotb.coroutine
    def drive_high(self):
        yield RisingEdge(self.clock)
        self.bus.SCL <= 1
        self.bus.SDA <= 1
        
    @cocotb.coroutine
    def send(self, transaction):
        self.bus.SCL <= 1
        self.bus.SDA <= 1
        for i in range(2*transaction.divider):
            yield RisingEdge(self.clock)
        self.bus.SDA <= 0
        for i in range(32):
            yield RisingEdge(self.clock)
            self.bus.SCL <= 0
            for j in range(transaction.divider):
                yield RisingEdge(self.clock)
            if (i%8==0) and (i > 0):
                self.bus.SCL <= 1
                yield RisingEdge(self.clock)
                self.bus.SCL <= 0
                for j in range(transaction.divider):
                    yield RisingEdge(self.clock)
            self.bus.SCL <= 1
            self.bus.SDA <= (transaction.data >> i) & 0x01
        yield RisingEdge(self.clock)
        self.bus.SCL <= 0
        for j in range(transaction.divider):
            yield RisingEdge(self.clock)
        self.bus.SCL <= 1
        yield RisingEdge(self.clock)
        self.bus.SCL <= 0
        for j in range(transaction.divider):
            yield RisingEdge(self.clock)
        self.bus.SCL <= 1
        self.bus.SDA <= 0
        yield RisingEdge(self.clock)
        self.bus.SDA <= 1
            
