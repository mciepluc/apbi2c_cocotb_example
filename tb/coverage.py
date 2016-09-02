import cocotb
from cocotb.coverage import CoverPoint
from cocotb.coverage import CoverCross
from cocotb.coverage import CoverCheck

from functools import wraps

class APBCoverage():
    def __call__(self, f):
        @wraps(f)
        @cocotb.coverage.CoverPoint("apb.delay", f = lambda xaction : xaction.delay, bins = range(0,10))
        @cocotb.coverage.CoverPoint("apb.addr",  f = lambda xaction : xaction.addr, bins = range(0,12,4))
        @cocotb.coverage.CoverPoint("apb.write", f = lambda xaction : xaction.write, bins = [True, False])
        @cocotb.coverage.CoverCross("apb.writeXdelay", items = ["apb.delay", "apb.write"])
        def _wrapped_function(*cb_args, **cb_kwargs):
            return f(*cb_args, **cb_kwargs)
        return _wrapped_function
