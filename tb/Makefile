TOPLEVEL := i2c
TOPLEVEL_LANG := verilog

PWD=$(shell pwd)
DUT = $(PWD)/../apbi2c/rtl

VERILOG_SOURCES = $(DUT)/apb.v $(DUT)/fifo.v $(DUT)/i2c.v $(DUT)/module_i2c.v

MODULE := test_i2c

include $(shell cocotb-config --makefiles)/Makefile.sim
