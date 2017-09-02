This is an example testbench using **cocotb** framework for **apbi2c** controller from freecores.
The intention is to present advanced metric-driven and constrained-random functional verification techniques using pure Python-based implementation.
No support of hardware verification languages such as e or SystemVerilog is required, which enables use of an arbitrary basic HDL simulator for the entire verification process. 

* COCOTB documentation http://cocotb.readthedocs.org
* Freecores repository http://freecores.github.io

The testbench contains all important parts of the advanced verification environment:
* external interface agents (for APB and I2C, in files apb.py and i2c.py),
* functional coverage as a verification plan (coverage.py),
* simple data integrity checking between interfaces (elementary scoreboarding),
* test sequences (for I2C read, I2C write and APB R/W operations),
* constrained randomization (for generating sequences),
* coverage-driven test scenario adjustment.

Additionaly, testbench presents the idea of checkpointing, which is storing of a specific simulation state of the DUT, to be used later for various test sequences, starting from the same point. This option can be disabled.

There are number of issues with **apbi2c** controller discovered with this testbench.
The test completes successfully only with checkpointing option enabled, as this prevents from continuing operation of the DUT at lock-up state. There are number of errors reported, such as:
* problems with APB read operations ('x' on the interface),
* incorrect handling I2C read operations (probably the controller does not recognize a start bit correctly),
* not all clock divider settings are working correctly,
* FIFO overflow is not reported. 
