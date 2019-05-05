#!/usr/bin/env python3
import time, logging, os, ast
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

#have not yet solved this for BITS=8
#good candidate for
#https://github.com/marijnheule/CnC
BITS=8
#must be even to calculate branch number
assert(BITS%2 == 0)

def half_branch(x):
    #returns:
    # 0 if x==0
    # 2 if the upper and lower half of x have
    #  a set bit
    # 1 if the upper half of x has a set bit
    #  or the lower half of x has a set bit
    lo,hi = 0,0
    for i in range(BITS):
        lo |= (x>>i)&1
        hi |= (x>>(i+BITS//2))&1
    return lo+hi

def half_branch8(i0):
    #same as above but more efficent 
    #BITS must be a power of 2, currently configured
    # only for when BITS=8
    #Uses the fast hamming weight masks
    m1 = int(   "01"   *(BITS//2),2)
    m2 = int(  "0011"  *(BITS//4),2)
    m4 = int("00001111"*(BITS//8),2)
    i1 = (i0&m1) | ((i0>>1)&m1)
    i2 = (i1&m2) | ((i1>>2)&m2)
    i4 = (i2&m4) + ((i2>>4)&m4)
    return i4

def branch(f,x,y):
    #in difference + out difference
    b = half_branch8 if BITS==8 else half_branch
    return b(x^y)+b(f[x]^f[y])

def branch_no_math(f,x,y):
    partial_bnum = half_branch(x^y)
    out_diff = f[x]^f[y]
    lo = Extract((BITS//2)-1,       0, out_diff) != 0
    hi = Extract(     BITS-1, BITS//2, out_diff) != 0
    if partial_bnum == 2:
        return Or(hi,lo)
    else:
        return And(hi,lo)

def get_saved_data(b):
    #load saved data
    save_file = "saved%d.txt"%b
    previous_sboxs = []
    if os.path.exists(save_file):
        logger.debug("open %r for reading", save_file)
        with open(save_file, "r") as f:
            for line in f:
                #ast.literal_eval is "safe" lol
                previous_sboxs.append(ast.literal_eval(line))
    else:
        logger.debug("%r does not exist", save_file)
    return previous_sboxs

def save_data(b,data):
    save_file = "saved%d.txt"%b
    with open(save_file, "a") as f:
        f.write(data)

if __name__ == "__main__":
    previous_sboxs = get_saved_data(BITS)
    #have not yet got the parallel to work
    #https://stackoverflow.com/questions/53246030/parallel-solving-in-z3
    #https://github.com/Z3Prover/z3/issues/2207
    set_option("parallel.enable", True)
    set_option("parallel.threads.max", 8)
    s = SolverFor("QF_BV")
    #No z3.Function needed with discrete indicies
    sbox = [BitVec("s%02x"%x, BITS) for x in range(2**BITS)]
    post_add = [(x+int("01"*(BITS//2),2))&((1<<BITS)-1) for x in post_add]
    #assert uniqness
    for other in previous_sboxs:
        #there shouldn't be a simple xor change between the two
        for diff in range(2**BITS):
            s.add(z3.Or(*(o^diff!=x for o,x in zip(other,sbox))))
    #assert branch numbers
    for i in range(2**BITS):
        for j in range(i+1,2**BITS):
            #at least 1 element will have a bnum of 4
            s.add(branch_no_math(sbox,i,j))
            # s.add(branch_no_math(post_add,i,j))
    #see if the assertions are satisfiable
    start = time.time()
    logger.debug("check")
    r = s.check()
    logger.debug("%r after %d sec.", r, time.time()-start)
    if r == sat:
        #extract the sbox values as python ints
        m = s.model()
        F = [m.eval(x).as_long() for x in sbox]
        logger.info(','.join(
            "{{:0{}b}}".format(BITS).format(x) for x in F
        ))
        #append this entry to the save file
        save_data(BITS, str(F)+"\n")
    # hook(locals())