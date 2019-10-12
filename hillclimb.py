#!/usr/bin/env python3
from common import hook, parse_args, fatal
import argparse, logging
logger = logging.getLogger(__name__)

from random import shuffle
from itertools import chain

class Perm(list):
    def __init__(self,*args):
        list.__init__(self,*args)
        self.cache = None
    def swap(self,x,y):
        self.cache = None
        self[x],self[y] = self[y],self[x]
    def __getitem__(self,x):
        r = list.__getitem__(self, x)
        return Perm(r) if type(r) == list else r
    def copy(self):
        return Perm(list.copy(self))
    def get_rows(l):
        return (l[r:r+0x10] for r in range(0,0x100,0x10))
    def get_cols(l):
        return (l[r:0x100:0x10] for r in range(0,0x10))
    def score(self):
        if self.cache:
            return self.cache
        uh = [x&0xf0 for x in self]
        lh = [x&0x0f for x in self]
        #partial match scores
        row_scores = [
            len(set(u)) + len(set(l)) for u,l in zip(
                Perm.get_rows(uh),Perm.get_rows(lh)
            )
        ]
        col_scores = [
            len(set(u)) + len(set(l)) for u,l in zip(
                Perm.get_cols(uh),Perm.get_cols(lh)
            )
        ]
        #full match score
        total = sum(
            x+0x10000 if x==0x20 else x for x in chain(
                row_scores, col_scores
            )
        )
        self.score_cache = total
        return total
    def __repr__(self):
        return '\n'.join(
            ' '.join(
                "{:02x}".format(x)
                for x in self[i:i+0x10]
            )
            for i in range(0,0x100,0x10)
        )

def level(p):
    best = (0, 0, p.score())
    for i in range(0x10,0x100-1):
        for j in range(i+1,0x100):
            p.swap(i,j)
            round_score = p.score()
            if round_score > best[2]:
                best = (i, j, round_score)
            p.swap(i,j)
    p.swap(best[0],best[1])
    return best[2]

def main(out, **kwargs):
    logger.debug("main(%r)", locals())
    score = 0
    while score != 2098176:
        first_row = [
            (x<<4)|x
            for x in range(0x10)
        ]
        choices = list(set(range(0x100))-set(first_row))
        shuffle(choices)
        p = Perm(first_row + choices)
        while p.score() != level(p):
            print(p)
            print("{:07d}/{:07d}".format(p.score(),2098176))
            print("-"*(16*3))
        score = p.score()
    
   
if __name__ == "__main__":
    #make the argument parser
    parser = argparse.ArgumentParser(
        description="This program will generate a sbox with branch "
            "number 3.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    #call main
    main(**parse_args(parser, root_logger=False))
