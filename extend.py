#!/usr/bin/env python3
import time
from z3 import *

from gen import *

BITS = 12

if __name__ == '__main__':
    #have not yet got the parallel to work
    #https://stackoverflow.com/questions/53246030/parallel-solving-in-z3
    #https://github.com/Z3Prover/z3/issues/2207
    set_option("parallel.enable", True)
    set_option("parallel.threads.max", 15)
    s = SolverFor("QF_BV")
    
    saved_sbox = get_saved_data(BITS//2)[0]
    x, y = z3.BitVecs("x y", BITS)
    sbox = z3.Function("sbox", z3.BitVecSort(BITS//2), z3.BitVecSort(BITS//2))
    s.add(*(sbox(i)==x for i,x in enumerate(saved_sbox)))
    mask = (1<<(BITS//2))-1
    hamming_shift = lambda x: (x+int("01"*(BITS//2),2))&((1<<BITS)-1)
    f = lambda x: hamming_shift(
         ZeroExt(BITS//2,sbox(Extract((BITS//2)-1, 0,x))) |
        (ZeroExt(BITS//2,sbox(Extract(BITS-1,BITS//2,x)))<<((BITS//2)-1))
    )
    #assert negation (we want everything to be >=3)
    s.add((half_branch(x^y)+half_branch(f(x)^f(y)))<3)

    #see if the assertions are satisfiable
    start = time.time()
    logger.debug("check")
    r = s.check()
    logger.debug("%r after %d sec.", r, time.time()-start)
    if r == sat:
        #extract the sbox values as python ints
        m = s.model()

    hook(locals())