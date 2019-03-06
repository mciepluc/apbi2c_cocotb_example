This is an example testbench using the **cocotb** framework for the **apbi2c** controller from freecores.
The intention is to present advanced metric-driven and constrained-random functional verification techniques using a pure Python-based implementation.
No support of hardware verification languages such as _e_ or SystemVerilog is required, which enables use of an arbitrary basic HDL simulator for the entire verification process. 

* cocotb documentation http://cocotb.readthedocs.org
* Freecores repository http://freecores.github.io

This testbench is used as an example in the [Article published in Jorunal of Electronic Testing](https://link.springer.com/article/10.1007/s10836-019-05777-0).

The testbench contains all important parts of an advanced verification environment:
* external interface agents (for APB and I2C, in files ``apb.py`` and ``i2c.py``),
* functional coverage as a verification plan (``coverage.py``),
* simple data integrity checking between interfaces (elementary scoreboarding),
* test sequences (for I2C read, I2C write and APB R/W operations),
* constrained randomization (for generating sequences),
* coverage-driven test scenario adjustment.

Additionally, the testbench presents the idea of checkpointing, which is storing a specific simulation state of the DUT, to be used later for various test sequences, starting from the same point. This option can be disabled.

There are a number of issues with the **apbi2c** controller, discovered with this testbench.
The test completes successfully only with the checkpointing option enabled, as this prevents from continuing operation of the DUT at lock-up state. There are a number of errors discovered, such as:
* problems with APB read operations (``'x'`` on the interface),
* incorrect handling of I2C read operations (probably the controller does not recognize a start bit correctly),
* not all clock divider settings are working correctly,
* FIFO overflow is not reported.
