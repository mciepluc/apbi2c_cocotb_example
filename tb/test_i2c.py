import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly, NextTimeStep, Event
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.result import ReturnValue, TestFailure
from cocotb.scoreboard import Scoreboard
from apb import APBSlave, APBTransaction

@cocotb.test()  
def test(dut):
    dut.log.info("Running test \"APBI2C CORE TEST\"!")
    yield Timer(1000000)
