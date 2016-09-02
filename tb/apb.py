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
        self.prev_address = 0 #used for coverage
        
    @cocotb.coroutine
    def send(self, transaction):
        rval = 0
        yield RisingEdge(self.clock)
        self.bus.PADDR <= transaction.addr
        self.bus.PWDATA <= transaction.data
        self.bus.PSELx <= 1
        self.bus.PWRITE <= 1 if transaction.write else 0
        yield RisingEdge(self.clock)
        self.bus.PENABLE <= 1
        while True:
            yield ReadOnly()
            if self.bus.PREADY.value:
                rval = self.bus.PRDATA.value
                break
            yield RisingEdge(self.clock)
        yield RisingEdge(self.clock)
        self.bus.PADDR <= 0
        self.bus.PWDATA <= 0
        self.bus.PSELx <= 0
        self.bus.PWRITE <= 0
        self.bus.PENABLE <= 0
        for i in range(transaction.delay):
            yield RisingEdge(self.clock)
        raise ReturnValue(rval)

    @cocotb.coroutine
    def _monitor_recv(self):
        delay = 0
        while True:
            yield RisingEdge(self.clock)
            yield ReadOnly()
            if (self.bus.PENABLE.value == 1) & (self.bus.PREADY.value == 1):
                data = self.bus.PWDATA.value if self.bus.PWRITE.value else self.bus.PRDATA.value
                xaction = APBTransaction(self.bus.PADDR.value, data, self.bus.PWRITE.value == 1, delay)
                delay = 0
                self._recv(xaction)
            else:
                delay = delay + 1
