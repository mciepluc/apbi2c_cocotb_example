import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly, NextTimeStep, Event
from cocotb.binary import BinaryValue
from cocotb.drivers import BusDriver
from cocotb.monitors import BusMonitor
from cocotb.binary import BinaryValue
from cocotb.decorators import coroutine
from cocotb.clock import Clock
from cocotb.result import ReturnValue, TestFailure
from cocotb.coverage import CoverPoint
from cocotb.crv import Randomized

class APBTransaction(Randomized):

    def __init__(self, address, data=0, write=False, delay=1):
        Randomized.__init__(self)
        self.addr = address
        self.data = data
        self.write = write
        self.delay = delay
        
        self.addRand("delay", range(0,10))

class APBSlave(BusDriver, BusMonitor):
    '''
    APB Slave
    '''
    _signals = [
        "pwrite", "psel", "penable", "paddr",  "pwdata", 
        "pready",  "prdata"
        ]

    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)
        BusMonitor.__init__(self, entity, name, clock)
        self.clock = clock
        self.bus.pwrite.setimmediatevalue(0)
        self.bus.psel.setimmediatevalue(0)
        self.bus.penable.setimmediatevalue(0)
        self.bus.paddr.setimmediatevalue(0)
        self.bus.pwdata.setimmediatevalue(0)
        self.prev_address = 0 #used for coverage
        
    @cocotb.coroutine
    def send(self, transaction):
        rval = 0
        yield RisingEdge(self.clock)
        self.bus.paddr <= transaction.addr
        self.bus.pwdata <= transaction.data
        self.bus.psel <= 1
        self.bus.pwrite <= 1 if transaction.write else 0
        yield RisingEdge(self.clock)
        self.bus.penable <= 1
        while True:
            yield ReadOnly()
            if self.bus.pready.value:
                rval = self.bus.prdata.value
                break
            yield RisingEdge(self.clock)
        yield RisingEdge(self.clock)
        self.bus.paddr <= 0
        self.bus.pwdata <= 0
        self.bus.psel <= 0
        self.bus.pwrite <= 0
        self.bus.penable <= 0
        for i in range(transaction.delay):
            yield RisingEdge(self.clock)
        raise ReturnValue(rval)

    @cocotb.coroutine
    def _monitor_recv(self):
        delay = 0
        while True:
            yield RisingEdge(self.clock)
            yield ReadOnly()
            if (self.bus.penable.value == 1) & (self.bus.pready.value == 1):
                data = self.bus.pwdata.value if self.bus.pwrite.value else self.bus.prdata.value
                xaction = APBTransaction(self.bus.paddr.value, data, self.bus.pwrite.value == 1, delay)
                delay = 0
                self._recv(xaction)
            else:
                delay = delay + 1
