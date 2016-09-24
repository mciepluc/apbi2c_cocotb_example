import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly, NextTimeStep, Event
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.result import ReturnValue, TestFailure
from cocotb.scoreboard import Scoreboard
from cocotb.coverage import reportCoverage
from i2c import I2CMonitor
from apb import APBSlave, APBTransaction
from coverage import APBCoverage
from coverage import I2CCoverage

@cocotb.coroutine
def apb_xaction_logger(logger, apb_monitor):
    
    @APBCoverage
    def log_xaction(xaction):
        logger.info("APB Transaction %s 0x%08X -> 0x%08X" % 
            ("Write" if xaction.write else "Read ", xaction.addr, xaction.data))
            
    while True:
        xaction = yield apb_monitor.wait_for_recv()
        log_xaction(xaction)
        
@cocotb.coroutine
def i2c_xaction_logger(logger, i2c_monitor):
    
    @I2CCoverage
    def log_xaction(xaction):
        logger.info("I2C Transaction 0x%08X" % xaction.data)
            
    while True:
        xaction = yield i2c_monitor.wait_for_recv()
        log_xaction(xaction)

@cocotb.test()
def test(dut):
    """Testing APBI2C core!"""
    log = cocotb.logging.getLogger("cocotb.test")
    cocotb.fork(Clock(dut.PCLK, 1000).start())

    apb = APBSlave(dut, name=None, clock=dut.PCLK)
    cocotb.fork(apb_xaction_logger(log, apb))
    
    i2c_monitor = I2CMonitor(dut, name=None, clock=dut.PCLK)
    cocotb.fork(i2c_xaction_logger(log, i2c_monitor))

    dut.PRESETn <= 0
    yield Timer(2000)
    dut.PRESETn <= 1
    yield Timer(8000)

    @cocotb.coroutine
    def config_write(addr, data):
        xaction = APBTransaction(addr, data, write=True)
        xaction.randomize()
        yield apb.send(xaction)

    @cocotb.coroutine
    def fifo_write(data):
        xaction = APBTransaction(0, data, write=True)
        xaction.randomize()
        yield apb.send(xaction)

    @cocotb.coroutine
    def fifo_read(data):
        xaction = APBTransaction(4, data, write=False)
        xaction.randomize()
        rdata = yield apb.send(xaction)
        raise rdata

    yield config_write(8, 0x0011)
    yield config_write(12, 0x0100)

    yield fifo_write(0x01234567)
    yield fifo_write(0x89ABCDEF)
 

    yield Timer(1000000)

    cocotb.coverage.reportCoverage(log.info, bins=True)

