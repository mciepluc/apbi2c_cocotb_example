TOPLEVEL := i2c
TOPLEVEL_LANG := verilog

PWD=$(shell pwd)
COCOTB=$(PWD)/../cocotb
DUT = $(PWD)/../apbi2c/rtl

#need to add cocotb-coverage to the PYTHONPATH
PYTHONPATH := ${PYTHONPATH}:$(PWD)/../cocotb-coverage

VERILOG_SOURCES = $(DUT)/apb.v $(DUT)/fifo.v $(DUT)/i2c.v $(DUT)/module_i2c.v

MODULE := test_i2c

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim
