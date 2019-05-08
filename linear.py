#!/usr/bin/env python3
import time, logging, os, ast

logger = logging.getLogger()
logging.basicConfig(format="%(levelname)9s:%(filename)s:%(message)s")
logger.setLevel(logging.DEBUG)

def hook(l=None):
    if l:
        locals().update(l)
    import IPython
    IPython.embed(banner1="", confirm_exit=False)
    exit(0)

BITS=4
MAXVAL = 2**BITS
MAXROW = 2**(BITS//2)

def fmt_merge(hi,lo):
	return (hi<<(BITS//2))|lo

def fmt_split(x):
	mask = (1<<(BITS//2))-1
	return (x>>(BITS//2))&mask, x&mask

if __name__ == "__main__":
	sbox = [0 for _ in range(MAXVAL)]
	avail_hi_row = {x:set(range(MAXROW)) for x in range(MAXROW)}
	avail_lo_row = {x:set(range(MAXROW)) for x in range(MAXROW)}
	avail_hi_col = {x:set(range(MAXROW)) for x in range(MAXROW)}
	avail_lo_col = {x:set(range(MAXROW)) for x in range(MAXROW)}
	avail = set(range(MAXVAL))
	#what's available at a position is
	#hi = avail_hi_row[i].union(avail_hi_col[j])
	#lo = avail_lo_row[i].union(avail_lo_col[j])
	#together = set(fmt_merge(x,y) for x,y in map(fmt_split,avail) if x in hi and y in lo)
	hook(locals())
