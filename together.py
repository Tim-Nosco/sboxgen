#!/usr/bin/env python3
from Crypto.Util.number import \
    long_to_bytes as l2b, bytes_to_long as b2l
from functools import reduce
import itertools as it
import linear
from common import hook, parse_args, fatal
import argparse
import logging
import random
import sys
logger = logging.getLogger(__name__)


# E(m, k<128>, bk<128>) = c
# D(c, k<128>, bk<128>) = m


def chunks(iterable, n, fillvalue=None):
    # https://docs.python.org/2/library/itertools.html#recipes
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return it.zip_longest(fillvalue=fillvalue, *args)


def gen_box_key(num_boxes=4):
    boxes = [
        linear.main(out=open('/dev/null','w'))
        #linear.main(out=sys.stdout)
        for _ in range(num_boxes)
    ]
    key = [box[x] for x in linear.special for box in boxes]
    return bytes(key)


def rol(val, r_bits, max_bits):
    #https://www.falatic.com/index.php/108/python-and-bitwise-rotation
    return (val << r_bits % max_bits) & (2**max_bits-1) | \
        ((val & (2**max_bits-1)) >> (max_bits-(r_bits % max_bits)))


def expand_key(key: bytes, num_keys: int = 16):
    random.seed(b2l(key))
    sbox_key = gen_box_key(num_keys)
    keys = b''
    for i in range(num_keys):
        keys += encrypt_block(
            key, 
            l2b(i).rjust(len(key),b'\x00')*num_keys, 
            sbox_key, 
            len(key)
        )
    return keys, sbox_key


def apply_sbox(b: int, key: list, block_size: int = 16):
    #fix keys
    key = [b2l(l2b(x)*block_size) for x in key]
    #extract upper and lower halfs
    uh, lh = b & int('f0'*block_size, 16), b & int('0f'*block_size, 16)
    c = lh | (lh << 4)
    #uh>=1
    p = (uh & int('10'*block_size, 16)) >> 4
    p |= p << 1
    p |= p << 2
    p |= p << 4
    c ^= key[0] & p
    #uh>=2
    p = (uh & int('20'*block_size, 16)) >> 5
    p |= p << 1
    p |= p << 2
    p |= p << 4
    c ^= key[1] & p
    #uh>=4
    p = (uh & int('40'*block_size, 16)) >> 6
    p |= p << 1
    p |= p << 2
    p |= p << 4
    c ^= key[2] & p
    #uh>=8
    p = (uh & int('80'*block_size, 16)) >> 7
    p |= p << 1
    p |= p << 2
    p |= p << 4
    c ^= key[3] & p
    logger.debug("%032x", c)
    return c


def encrypt_round(
    m: bytes, 
    key: bytes, sbox_key: bytes, 
    block_size: int
):
    logger.debug("%032x, %032x, %08x", b2l(m), b2l(key), b2l(sbox_key))
    #format inputs
    c, key = b2l(m), b2l(key)
    #test high bit of key
    t = (key & (1 << (block_size-1))) >> (block_size-1)
    #non-linear addition
    c += int('10'*(block_size//2), 2) >> t
    #mix in the key
    c ^= key
    #apply rotate to sbox key
    rotate_amount = 4 << t
    sbox = [rol(x, rotate_amount, 8) for x in sbox_key]
    #apply sbox
    c = apply_sbox(c, sbox)
    #rotate full ciphertext
    c = rol(c, 4*5, block_size*8)
    #format result
    return l2b(c)


def encrypt_block(
    m: bytes, 
    expanded_key: bytes, sbox_key: bytes, 
    block_size: int
):
    return reduce(lambda ct,round_num: 
        encrypt_round(
            ct,
            expanded_key[
                round_num*block_size:round_num*block_size+block_size
            ],
            sbox_key[round_num*4:round_num*4+4],
            block_size
        ),
        range(block_size), m
    )


def main(out, **kwargs):
    logger.debug("main(%r)", locals())


if __name__ == "__main__":
    #make the argument parser
    parser = argparse.ArgumentParser(
        description="This program implements a custom cipher.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    #call main
    main(**parse_args(parser, root_logger=False))
