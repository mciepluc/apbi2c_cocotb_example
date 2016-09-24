import cocotb
from cocotb.triggers import RisingEdge, ReadOnly
from cocotb.binary import BinaryValue
from cocotb.drivers import BusDriver
from cocotb.monitors import BusMonitor
from cocotb.decorators import coroutine
from cocotb.crv import Randomized

class I2CTransaction(Randomized):

    def __init__(self, data=0, write=False):
        Randomized.__init__(self)
        self.data = data
        self.write = write

class I2CMonitor(BusMonitor):
    '''
    APB Slave
    '''
    _signals = ["SDA", "SCL"]

    def __init__(self, entity, name, clock):
        BusMonitor.__init__(self, entity, name, clock)
        self.clock = clock
        
    @cocotb.coroutine
    def _monitor_recv(self):
        started = False
        prev_scl = 1
        while True:
            yield RisingEdge(self.clock)
            yield ReadOnly()
            #start bit
            if (not started) & (self.bus.SDA.value == 0) & (self.bus.SCL.value == 1):
                started = True
                rdata = 0
                data_cnt = 0
                ack = 1
            #sample data at SCL
            elif started & (self.bus.SCL.value == 1) & (prev_scl == 0):
                prev_scl = 1
                if data_cnt == 32:
                    started = False
                    xaction = I2CTransaction(rdata, write=False)
                    self._recv(xaction)
                elif (data_cnt%8 != 0) | ack:
                    ack = 0
                    rdata = rdata + (self.bus.SDA.value << data_cnt)
                    data_cnt += 1
                else: #ack state
                    ack = 1
            elif started & (self.bus.SCL.value == 0):
                prev_scl = 0
