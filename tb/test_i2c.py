
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
Testbench of the apbi2c controller - top level containing main test logic

"""

import random
import cocotb

from cocotb.triggers import ReadOnly
from cocotb.clock import Clock, Timer
from cocotb.result import ReturnValue, TestFailure
from cocotb.scoreboard import Scoreboard
from cocotb.crv import Randomized
from cocotb.coverage import reportCoverage
from cocotb.utils import get_sim_time

from apb import *
from checkpoint import *
from coverage import *
from i2c import *

#enable detailed logging of APB and I2C transactions
LOG_XACTION_ENABLE = True
#enable usage of checkpoints during the test
ENABLE_CHECKPOINTS = True

@cocotb.test()
def test_tree(dut):
    """Testing APBI2C core"""
    
    log = cocotb.logging.getLogger("cocotb.test")
    cocotb.fork(Clock(dut.PCLK, 1000).start())

    #instantiate the APB agent (monitor and driver) (see apb.py)
    apb = APBSlave(dut, name=None, clock=dut.PCLK)
    
    #instantiate the I2C monitor and driver (see i2c.py)
    i2c_monitor = I2CMonitor(dut, name="", clock=dut.PCLK)
    i2c_driver = I2CDriver(dut, name=None, clock=dut.PCLK)
            
    #write to config register via APB
    @cocotb.coroutine
    def config_write(addr, data):
        xaction = APBTransaction(addr, data, write=True)
        xaction.randomize()
        yield apb.send(xaction)
            
    #store observed I2C transactions
    received_i2c_xactions = []
    
    #the catcher for observerd I2C transaction on the interfece
    @I2CCoverage
    def i2c_xaction_catcher(i2c_xaction):
        if LOG_XACTION_ENABLE:
            log.info("I2C Monitor: Transaction 0x%08X" % i2c_xaction.data)
        received_i2c_xactions.append(i2c_xaction)
        
    #add callback to the monitor to call the catcher when I2C transaction observed
    i2c_monitor.add_callback(i2c_xaction_catcher)
    
    #the catcher for observerd APB transaction on the interfece
    @APBCoverage
    def apb_xaction_catcher(apb_xaction):
        if LOG_XACTION_ENABLE:
            try:
                log.info("APB Transaction %s 0x%08X -> 0x%08X" % 
                    ("Write" if apb_xaction.write else "Read ", apb_xaction.addr, apb_xaction.data))
            except:
                log.info("APB Transaction %s 0x%08X -> 0x%08s" % 
                    ("Write" if apb_xaction.write else "Read ", apb_xaction.addr, apb_xaction.data))
                
    #add callback to the monitor to call the catcher when APB transaction observed
    apb.add_callback(apb_xaction_catcher)
    
    #define "I2C Operation" as a bunch of r/ws with defined number of data and a specific clock divider
    #this is the main stuff to be tested - we want to know if controller correctly processes
    #transfers with different directions, amount of data and SCK period
    class I2C_Operation(Randomized):
        def __init__(self, direction = 'write', repeat = 1, divider = 1):
            Randomized.__init__(self)
            self.direction = direction
            self.repeat = repeat
            self.divider = divider
            self.repeat_range = (1,3)
            self.divider_range = (1,3)
            
            #I2C_Operation objects may be fully randomized
            self.addRand("direction",["write", "read"])
            self.addRand("repeat_range",[(1,3), (4,7), (8,15), (16,31)])
            self.addRand("divider_range",[(1,3), (4,7), (8,15), (16,31)])
        
        #post_randomize used to pick random values from already randomized ranges
        def post_randomize(self):
            self.repeat = random.randint(self.repeat_range[0], self.repeat_range[1])
            self.divider = random.randint(self.divider_range[0], self.divider_range[1])
            
    #list of completed operations for the summary
    operations_completed = []
    
    #function sampling operations coverage (see coverage.py)
    @OperationsCoverage
    def sample_operation(direction, repeat, divider, ok):
        operations_completed.append((direction, repeat, divider, ok))
        if ok:
            log.info("Operation %s of %d words with divider %d finished successfully" % 
              (direction, repeat, divider))
        else:
            log.error("Operation %s of %d words with divider %d finished with error!" % 
              (direction, repeat, divider))
              
    #function sampling operations order coverage (see coverage.py)
    @OperationsOrderCoverage
    def sample_operations_order_coverage(prev_direction, direction):
        pass
              
    #a test sequence - complete I2C Write Operation
    @cocotb.coroutine
    def segment_i2c_write_operation(operation):
        expected_out = []
        yield config_write(8, 0x0001 | (operation.divider << 2))
        
        #create xaction objects and fill FIFO up via APB with data to be send
        apb_xaction = APBTransaction(0, 0, write=True)
        for i in range(operation.repeat):
            i2c_xaction = I2CTransaction(0, write=False)
            i2c_xaction.randomize()
            apb_xaction.data = i2c_xaction.data
            apb_xaction.randomize()
            yield apb.send(apb_xaction)
            expected_out.append(i2c_xaction)
        
        #wait for FIFO empty - meaning all data sent out
        guard_int = 0
        while not dut.INT_TX.value:
            guard_int = guard_int + 1
            yield RisingEdge(dut.PCLK)
            if guard_int == 50000:
                raise TestFailure("Controller hang-up!")
            
        #a simple scoreboarding...
        #compare data written to APB with catched on I2C interface
        ok = True
        received_xactions = received_i2c_xactions[-operation.repeat:]
        if len(received_xactions) < operation.repeat:
            ok = False
        else:
            for i in range(operation.repeat):
                if (received_xactions[i] != expected_out[i]):
                    ok = False
                    break
        
        #call sampling at the and of the sequence
        sample_operation("write", operation.repeat, operation.divider, ok)
        
    #a test sequence - complete I2C Read Operation
    @cocotb.coroutine
    def segment_i2c_read_operation(operation):
        expected_in = []
        yield config_write(8, 0x0002 | (operation.divider << 2))
        
        #create I2C xaction objects and send on the interface
        for i in range(operation.repeat):
            i2c_xaction = I2CTransaction(0, write=True)
            i2c_xaction.randomize()
            expected_in.append(i2c_xaction)
            yield i2c_driver.send(i2c_xaction)
        
        #a simple scoreboarding...
        #compare data written on I2C interface with read from FIFO
        ok = True
        apb_xaction = APBTransaction(0x04, 0, write=False)
        for i in range(operation.repeat):
            try:
                apb_xaction.randomize()
                rdata = yield apb.send(xaction)
                if (rdata != expected_in[i].data):
                    ok = False
            except:
                log.error("APB read data from FIFO is 'X'")
                ok = False
                
        #call sampling at the and of the sequence
        sample_operation("read", operation.repeat, operation.divider, ok)
        
    #a test sequence - APB registers operation (sort of UVM_REG :) )
    @cocotb.coroutine
    def segment_apb_rw(repeat = 1, addr = 0xC):
        
        apb_xaction_wr = APBTransaction(addr, 0, write=True)
        apb_xaction_rd = APBTransaction(addr, 0, write=False)
        
        #just do some APB/RW
        for i in range(repeat):
            data = random.randint(0,0xFFFFFFFF)
            apb_xaction_wr.randomize()
            apb_xaction_wr.data = data
            yield apb.send(apb_xaction_wr)
            apb_xaction_rd.randomize()
            rdata = yield apb.send(apb_xaction_rd)
            try:
                if rdata != data:
                    log.error("APB read data @ 0x%08X does not match written value" % addr)
            except:
                log.error("APB read data @ 0x%08X is 'X'" % addr)
                
    #reset the DUT
    dut.PRESETn <= 0
    yield Timer(2000)
    dut.PRESETn <= 1
    
    yield config_write(12, 0x0100)

    #if checkpoints used, store them in the map, (see checkpoint.py)
    if ENABLE_CHECKPOINTS:
        checkpoints = {}
        get_checkpoint_hier(dut)
        #the fist checkpoint is just after reset
        checkpoints['init'] = (checkpoint(), None)
    
    #list of already covered operations, used to constraint the randomization
    already_covered = []
    
    #constraint for the operation randomization - do not use already covered combinations
    def op_constraint(direction, divider_range, repeat_range):
        return not (direction, repeat_range, divider_range) in already_covered
        
    #previous I2C operation, used for OperationsOrderCoverage (see coverage.py)
    i2c_op_prev = None
    
    #we define test end condition as reaching 99% coverage at the op.cross cover item
    cov_op_cross = 0
    while cov_op_cross < 99:
        
        #restore randomly selected checkpoint
        if ENABLE_CHECKPOINTS:
            chkp_to_restore = random.choice(checkpoints.keys())
            log.info("Restoring a simulation checkpoint: " + chkp_to_restore)
            current_chceckpoint = checkpoints[chkp_to_restore]
            restore(current_chceckpoint[0])
    
        #create I2C operation object to be executed
        i2c_op = I2C_Operation()
        i2c_op.randomize_with(op_constraint)
        already_covered.append((i2c_op.direction, i2c_op.repeat_range, i2c_op.divider_range))
        
        #call test sequence
        if i2c_op.direction == "read":
            yield segment_i2c_read_operation(i2c_op)
        else:
            yield segment_i2c_write_operation(i2c_op)
            
        if ENABLE_CHECKPOINTS:
            if operations_completed[-1][3]: #if status is OK, add this simulation point to the checkpoints list
                chkp_name = str(get_sim_time('ns'))
                log.info("Creating a simulation checkpoint: " + chkp_name)
                checkpoints[chkp_name] = (checkpoint(), i2c_op)
                
        #call APB test sequence as long as cover item apb.writeXdelay coverage level is below 100%
        if cocotb.coverage.coverage_db["apb.writeXdelay"].coverage*100/cocotb.coverage.coverage_db["apb.writeXdelay"].size < 100:
            yield segment_apb_rw(repeat = random.randint(1,5))
            
        
        #sample OperationsOrderCoverage (see coverage.py)
        if ENABLE_CHECKPOINTS:
            if current_chceckpoint[1] is not None:
                sample_operations_order_coverage(current_chceckpoint[1].direction, i2c_op.direction)
        else:
            if i2c_op_prev is not None:
                sample_operations_order_coverage(i2c_op_prev.direction, i2c_op.direction)
        
        i2c_op_prev = i2c_op
        
        #update the coverage level
        cov_op_cross = cocotb.coverage.coverage_db["op.cross"].coverage*100/cocotb.coverage.coverage_db["op.cross"].size
        log.info("Current op.cross coverage level = %d %%", cov_op_cross)
        
    #print summary
    log.info("Opertions finished succesfully:")
    for elem in operations_completed:
        if elem[3]:
            log.info("   %s of %d words with divider %d" % (elem[0], elem[1], elem[2]))
            
    log.info("Opertions finished with error:")
    for elem in operations_completed:
        if not elem[3]:
            log.info("   %s of %d words with divider %d" % (elem[0], elem[1], elem[2]))
            
    log.info("Functional coverage details:")
    cocotb.coverage.reportCoverage(log.info, bins=False)
    
