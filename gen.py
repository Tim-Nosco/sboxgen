#!/usr/bin/env python3
import time, logging
from z3 import *

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(levelname)9s:%(filename)s:%(message)s")
logger.setLevel(logging.DEBUG)

def hook(l=None):
    if l:
        locals().update(l)
    import IPython
    IPython.embed(banner1="", confirm_exit=False)
    exit(0)

BITS=8

def half_branch(x):
    lo,hi = 0,0
    for i in range(BITS):
        lo |= (x>>i)&1
        hi |= (x>>(i+BITS//2))&1
    return lo+hi

def half_branch8(i0):
    m1 = int(   "01"   *(BITS//2),2)
    m2 = int(  "0011"  *(BITS//4),2)
    m4 = int("00001111"*(BITS//8),2)
    i1 = (i0&m1) | ((i0>>1)&m1)
    i2 = (i1&m2) | ((i1>>2)&m2)
    i4 = (i2&m4) + ((i2>>4)&m4)
    return i4

def branch(f,x,y):
    b = half_branch8 if BITS==8 else half_branch
    return b(x^y)+b(f(x)^f(y))

if __name__ == "__main__":
    set_option("parallel.enable", True)
    set_option("parallel.threads.max", 15)
    s = SolverFor("QF_BV")
    sbox = Function("sbox", BitVecSort(BITS), BitVecSort(BITS))
    for i in range(2**BITS):
        for j in range(i+1,2**BITS):
            s.add(branch(sbox,i,j)>=3)
    start = time.time()
    logger.debug("check")
    r = s.check()
    logger.debug("%r after %d sec.", r, time.time()-start)
    if r == sat:
        m = s.model()
        F = [m.eval(sbox(x)).as_long() for x in range(2**BITS)]
        logger.info(','.join(
            "{{:0{}b}}".format(BITS).format(x) for x in F
        ))
    hook(locals())