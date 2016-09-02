import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly, NextTimeStep, Event
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.result import ReturnValue, TestFailure
from cocotb.scoreboard import Scoreboard
from apb import APBSlave, APBTransaction
from coverage import APBCoverage

@cocotb.coroutine
def apb_xaction_logger(logger, apb_monitor):
    
    @APBCoverage()
    def log_xaction(xaction):
        logger.info("APB Transaction %s 0x%08X -> 0x%08X" % 
            ("Write" if xaction.write else "Read ", xaction.addr, xaction.data))
            
    while True:
        xaction = yield apb_monitor.wait_for_recv()
        log_xaction(xaction)

@cocotb.test()  
def test(dut):
    """Testing APBI2C core!"""
    log = cocotb.logging.getLogger("cocotb.test")
    cocotb.fork(Clock(dut.PCLK, 1000).start())

    apb = APBSlave(dut, name=None, clock=dut.PCLK)
    cocotb.fork(apb_xaction_logger(log, apb))

    dut.PRESETn <= 0
    yield Timer(2000)
    dut.PRESETn <= 1
    yield Timer(8000)

    @cocotb.coroutine
    def apb_write(data):
        xaction = APBTransaction(0, data, write=True)
        xaction.randomize()
        yield apb.send(xaction)

    yield apb_write(1)

    yield Timer(1000000)

