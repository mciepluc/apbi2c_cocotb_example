
'''Copyright (c) 2016-2024, Marek Cieplucha, https://github.com/mciepluc
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
import cocotb_coverage

from cocotb.triggers import ReadOnly
from cocotb.clock import Clock, Timer
from cocotb.result import ReturnValue, TestFailure
from cocotb_bus.scoreboard import Scoreboard
from cocotb.utils import get_sim_time

from cocotb_coverage.crv import Randomized
from cocotb_coverage.coverage import coverage_db
from cocotb_checkpoint.checkpoint import *

from apb import *
#from checkpoint import *
from coverage import *
from i2c import *

#enable detailed logging of APB and I2C transactions
LOG_XACTION_ENABLE = False

#enable usage of checkpoints during the test 
ENABLE_CHECKPOINTS = True

#if set false, corresponds to standard regression suite where tests are started
#from the init state, when true, tests may be started from already achieved 
#state, which enables faster coverage closure
CHECKPOINTS_TREE_STRUCTURE = True

@cocotb.test
async def test_tree(dut):
    """Testing APBI2C core"""
    
    log = cocotb.logging.getLogger("cocotb.test")
    cocotb.start_soon(Clock(dut.PCLK, 1000).start())

    #instantiate the APB agent (monitor and driver) (see apb.py)
    apb = APBSlave(dut, name=None, clock=dut.PCLK)
    
    #instantiate the I2C monitor and driver (see i2c.py)
    i2c_monitor = I2CMonitor(dut, name="", clock=dut.PCLK)
    i2c_driver = I2CDriver(dut, name=None, clock=dut.PCLK)
            
    #write to config register via APB
    async def config_write(addr, data):
        xaction = APBTransaction(addr, data, write=True)
        xaction.randomize()
        await apb.send(xaction)
            
    #store observed I2C transactions
    received_i2c_xactions = []
    
    #the catcher for observerd I2C transaction on the interfece
    @I2CCoverage
    def i2c_xaction_catcher(i2c_xaction):
        if LOG_XACTION_ENABLE:
            log.info("I2C Monitor: Transaction 0x%08X" % i2c_xaction.data)
        received_i2c_xactions.append(i2c_xaction)
        
    #callback to the monitor to call the catcher when I2C transaction observed
    i2c_monitor.add_callback(i2c_xaction_catcher)
    
    #the catcher for observerd APB transaction on the interfece
    @APBCoverage
    def apb_xaction_catcher(apb_xaction):
        if LOG_XACTION_ENABLE:
            try:
                log.info("APB Transaction %s 0x%08X -> 0x%08X" % 
                    ("Write" if apb_xaction.write else "Read ", 
                     int(apb_xaction.addr), int(apb_xaction.data))
                )
            except:
                log.info("APB Transaction %s 0x%08X -> 0x%08s" % 
                    ("Write" if apb_xaction.write else "Read ", 
                     int(apb_xaction.addr), int(apb_xaction.data))
                )
                
    #callback to the monitor to call the catcher when APB transaction observed
    apb.add_callback(apb_xaction_catcher)
    
    #define "I2C Operation" as a bunch of r/ws with defined number of data 
    #and a specific clock divider
    #this is the main stuff to be tested - we want to know if controller 
    #correctly processes transfers with different directions, amount of 
    #data and SCK period
    class I2C_Operation(Randomized):
        def __init__(self, direction = 'write', repeat = 1, divider = 1):
            Randomized.__init__(self)
            self.direction = direction
            self.repeat = repeat
            self.divider = divider
            self.repeat_range = (1,3)
            self.divider_range = (1,3)
            
            #I2C_Operation objects may be fully randomized
            self.add_rand("direction",["write", "read"])
            self.add_rand("repeat_range",
              [(1,3), (4,7), (8,11), (12,15), (16,23), (24,31)]
            )
            self.add_rand("divider_range",
              [(1,3), (4,7), (8,11), (12,15), (16,23), (24,31)]
            )
        
        #post_randomize to pick random values from already randomized ranges
        def post_randomize(self):
            self.repeat = random.randint(
              self.repeat_range[0], self.repeat_range[1]
            )
            self.divider = random.randint(
              self.divider_range[0], self.divider_range[1]
            )
            
    #list of completed operations for the summary
    operations_completed = []

    #function sampling operations order coverage (see coverage.py)
    @OperationsOrderCoverage
    def sample_operations_order_coverage(prev_operation, operation):
        pass
    
    #function sampling operations coverage (see coverage.py)
    @OperationsCoverage
    def sample_operation(operation, ok):
        operations_completed.append((operation, ok))
        if (len(operations_completed)>1):
            sample_operations_order_coverage(
             operations_completed[-2][0], operations_completed[-1][0]
            ) 
        if ok:
            log.info(
               "Operation %s of %d words, divider %d - OK!" % 
              (operation.direction, operation.repeat, operation.divider)
            )
        else:
            log.error(
               "Operation %s of %d words, divider %d - error!" % 
              (operation.direction, operation.repeat, operation.divider)
            )
              
              
    #a test sequence - complete I2C Write Operation
    async def segment_i2c_write_operation(operation):
        expected_out = []
        await config_write(8, 0x0001 | (operation.divider << 2))
        
        #create xaction objects and fill FIFO up via APB with data to be send
        apb_xaction = APBTransaction(0, 0, write=True)
        for i in range(operation.repeat):
            i2c_xaction = I2CTransaction(0, write=False)
            i2c_xaction.randomize()
            apb_xaction.data = i2c_xaction.data
            apb_xaction.randomize()
            await apb.send(apb_xaction)
            expected_out.append(i2c_xaction)
        
        #wait for FIFO empty - meaning all data sent out
        guard_int = 0
        while not dut.INT_TX.value:
            guard_int = guard_int + 1
            await RisingEdge(dut.PCLK)
            if guard_int == 50000:
                #raise TestFailure("Controller hang-up!")
                    ok = False
                    break
            
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
        sample_operation(operation, ok)
        
    #a test sequence - complete I2C Read Operation
    async def segment_i2c_read_operation(operation):
        expected_in = []
        await config_write(8, 0x0002 | (operation.divider << 2))
        
        #create I2C xaction objects and send on the interface
        for i in range(operation.repeat):
            i2c_xaction = I2CTransaction(0, write=True)
            i2c_xaction.randomize()
            expected_in.append(i2c_xaction)
            await i2c_driver.send(i2c_xaction)
        
        #a simple scoreboarding...
        #compare data written on I2C interface with read from FIFO
        ok = True
        apb_xaction = APBTransaction(0x04, 0, write=False)
        for i in range(operation.repeat):
            try:
                apb_xaction.randomize()
                rdata = await apb.send(xaction)
                if (rdata != expected_in[i].data):
                    ok = False
            except:
                if LOG_XACTION_ENABLE:
                    log.error("APB read data from FIFO is 'X'")
                ok = False
                
        #call sampling at the and of the sequence
        sample_operation(operation, ok)
        
    #a test sequence - APB registers operation (sort of UVM_REG :) )
    async def segment_apb_rw(repeat = 1, addr = 0xC):
        
        apb_xaction_wr = APBTransaction(addr, 0, write=True)
        apb_xaction_rd = APBTransaction(addr, 0, write=False)
        
        #just do some APB/RW
        for i in range(repeat):
            data = random.randint(0,0xFFFFFFFF)
            apb_xaction_wr.randomize()
            apb_xaction_wr.data = data
            await apb.send(apb_xaction_wr)
            apb_xaction_rd.randomize()
            rdata = await apb.send(apb_xaction_rd)
            if LOG_XACTION_ENABLE:
                try:
                    if rdata != data:
                        log.error(
                          "APB read data @ 0x%08X does not match written value" 
                          % addr
                        )
                except:
                    log.error("APB read data @ 0x%08X is 'X'" % addr)
                
    #reset the DUT
    dut.PRESETn.value = 0
    await Timer(2000)
    dut.PRESETn.value = 1
    
    await config_write(12, 0x0100)

    #if checkpoints used, store them in the map, (see checkpoint.py)
    if ENABLE_CHECKPOINTS:
        checkpoints = {}
        get_checkpoint_hier(dut)
        #the fist checkpoint is just after reset
        checkpoints['0'] = (checkpoint(), None)
    
    #list of already covered operations, used to constraint the randomization
    already_covered = []
    
    #constraint for the operation randomization - do not use already 
    #covered combinations
    def op_constraint(direction, divider_range, repeat_range):
        return not (direction, repeat_range, divider_range) in already_covered
    
    apb_cover_item = coverage_db["top.apb.writeXdelay"]
    top_cover_item = coverage_db["top"]
    
    #we define test end condition as reaching 90% coverage at the 
    #top cover item
    cov_op = 0
    while cov_op < 90:
        
        #restore randomly selected checkpoint
        if ENABLE_CHECKPOINTS:
            if CHECKPOINTS_TREE_STRUCTURE:
                chkp_to_restore = random.choice(list(checkpoints.keys()))
            else:
                chkp_to_restore = '0'

            log.info("Restoring a simulation checkpoint at %s ns" % 
                chkp_to_restore)
            current_chceckpoint = checkpoints[chkp_to_restore]
            restore(current_chceckpoint[0])
    
        #create I2C operation object to be executed
        i2c_op = I2C_Operation()
        #if there is no tree structure, knowledge about already covered 
        #cases cannot be used
        if ENABLE_CHECKPOINTS & CHECKPOINTS_TREE_STRUCTURE:
            try:
                i2c_op.randomize_with(op_constraint)
            except:
                i2c_op.randomize()
        else:
            i2c_op.randomize()
        already_covered.append(
          (i2c_op.direction, i2c_op.repeat_range, i2c_op.divider_range)
        )
        
        #call test sequence
        if i2c_op.direction == "read":
            await segment_i2c_read_operation(i2c_op)
        else:
            await segment_i2c_write_operation(i2c_op)
            
        if ENABLE_CHECKPOINTS:
            #if status is OK, add this simulation point to the checkpoints list
            if operations_completed[-1][1]: 
                chkp_name = str(get_sim_time('ns'))
                log.info("Creating a simulation checkpoint: " + chkp_name)
                checkpoints[chkp_name] = (checkpoint(), i2c_op)
                
        #call APB test sequence as long as cover item apb.writeXdelay 
        #coverage level is below 100%
        if apb_cover_item.coverage*100/apb_cover_item.size < 100:
            await segment_apb_rw(repeat = random.randint(1,5))
                    
        #update the coverage level
        
        cov_op_prev = cov_op
        cov_op = top_cover_item.coverage*100.0/top_cover_item.size
        log.info("Current overall coverage level = %f %%", cov_op)
        
    #print summary
    log.info("Opertions finished succesfully:")
    for elem in operations_completed:
        if elem[1]:
            log.info("   %s of %d words with divider %d" % 
              (elem[0].direction, elem[0].repeat, elem[0].divider)
            )
            
    log.info("Opertions finished with error:")
    for elem in operations_completed:
        if not elem[1]:
            log.info("   %s of %d words with divider %d" % 
              (elem[0].direction, elem[0].repeat, elem[0].divider)
            )
            
    log.info("Functional coverage details:")
    coverage_db.report_coverage(log.info, bins=False)
    coverage_db.export_to_xml("results_coverage.xml")
    
