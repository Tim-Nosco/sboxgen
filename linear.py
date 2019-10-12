#!/usr/bin/env python3
from common import hook, parse_args, fatal
import argparse, logging
logger = logging.getLogger(__name__)

from itertools import chain
from random import shuffle

class Stack(list):
    push = list.append
    def __getitem__(self,x):
        r = list.__getitem__(self, x)
        return Stack(r) if type(r) == list else r

class Assignment:
    def __init__(self, level, pos, val, state):
        self.pos, self.val = pos, val
        self.level, self.state = level, state
    def __repr__(self):
        return """{{level={:d}, pos={:02x}, val={:02x}}}\n{}""".format(
            self.level, self.pos, self.val, self.state
        )

class State:
    def __init__(self, setup=True):
        if not setup:
            return
        first_row = [
            (x<<4)|x
            for x in range(0x10)
        ]
        self.overall_available = set(range(0x100))-set(first_row)
        self.available = [set([x]) for x in first_row] + [
            self.overall_available.copy() for x in range(0x10,0x100)
        ]
    
        for i,x in enumerate(first_row):
            self.assign(i,x)

    def assign(self,pos,val):
        #update available
        #remove val from options
        self.overall_available.discard(val)
        for x in self.available:
            x.discard(val)
        #update shared column / row
        def influence(x):
            uh, lh = x&0xf0, x&0x0f
            return chain(range(lh,0x100,16),range(uh,uh+0x10))
        allowed = set(range(0x100))-set(influence(val))
        for p in influence(pos):
            self.available[p] = self.available[p].intersection(allowed)
        
        #fix up pos
        self.available[pos] = set([val])

    def is_valid(self, extra_check=False):
        part1 = all(self.available)
        return part1 and (
            not extra_check or len(self.overall_available)==0
        )

    def copy(self):
        s = State(False)
        s.overall_available = self.overall_available.copy()
        s.available = [x.copy() for x in self.available]
        return s
    
    def str_avail(s, pos):
        return ' '.join('{:02x}'.format(x) for x in s.available[pos])
    
    def __repr__(self):
        return '\n'.join(
            ' '.join(
                "{:02x}".format(list(x)[0]) if len(x)==1 else 'XX'
                for x in self.available[i:i+0x10]
            )
            for i in range(0,0x100,0x10)
        )

special = [0x10,0x20,0x40,0x80]

def level(state, idx=0):
    if idx >= len(special):
        return state if state.is_valid(True) else None
    options = list(state.available[special[idx]])
    shuffle(options)
    for parent in options:
        logger.debug("level: %d trying: %02x", idx,parent)
        state_copy = state.copy()
        for i in range(0, special[idx]):
            child = list(state_copy.available[i])
            if len(child) != 1:
                break
            state_copy.assign(
                special[idx]+i,
                child[0] ^ parent
            )
        else:
            #check logic, go to next round
            if state_copy.is_valid():
                logger.debug("\n%s", state_copy)
                result = level(state_copy, idx+1)
                if result:
                    return result

def main(out, **kwargs):
    logger.debug("main(%r)", locals())
    s = level(State())
    print(s)
    choices = [list(s.available[pos])[0]for pos in special]
    print("choices="+' '.join('{:02x}'.format(x) for x in choices))
    
if __name__ == "__main__":
    #make the argument parser
    parser = argparse.ArgumentParser(
        description="This program will generate a sbox with branch "
            "number 3.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    #call main
    main(**parse_args(parser, root_logger=False))
