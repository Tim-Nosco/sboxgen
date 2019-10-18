#!/usr/bin/env python3
from more_itertools import nth
import re
import colorama
from tqdm import trange
from scipy.stats import binom_test
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
import os
from binascii import hexlify as h
logger = logging.getLogger(__name__)


# E(m, k<128>, bk<128>) = c
# D(c, k<128>, bk<128>) = m


def chunks(iterable, n, fillvalue=None, m=None):
    # https://docs.python.org/2/library/itertools.html#recipes
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    r = it.zip_longest(fillvalue=fillvalue, *args)
    return map(m, r) if m else r


def gen_box_key(num_boxes=4):
    boxes = [
        linear.main(out=open('/dev/null', 'w'))
        #linear.main(out=sys.stdout)
        for _ in range(num_boxes)
    ]
    key = [box[x] for box in boxes for x in linear.special]
    return bytes(key)


def rol(val, r_bits, max_bits):
    #https://www.falatic.com/index.php/108/python-and-bitwise-rotation
    return (val << r_bits % max_bits) & (2**max_bits-1) | \
        ((val & (2**max_bits-1)) >> (max_bits-(r_bits % max_bits)))


def ror(val, r_bits, max_bits):
    return ((val & (2**max_bits-1)) >> r_bits % max_bits) | \
        (val << (max_bits-(r_bits % max_bits)) & (2**max_bits-1))


def expand_key(key: bytes, num_keys: int = 7):
    random.seed(b2l(key))
    sbox_key = gen_box_key(num_keys)
    keys = b''
    for i in range(num_keys):
        keys += encrypt_block(
            key,
            l2b(i).rjust(len(key), b'\x00')*num_keys,
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
    #mix in the key
    c ^= key
    #apply sbox
    c = apply_sbox(c, sbox_key)
    #lower halfs shuffle
    m = int('f0'*block_size, 16)
    uh, lh = c & m, c & (m >> 4)
    c = uh | rol(lh, 8*7, block_size*8)
    #c = uh | rol(lh, 8*(round_num+1), block_size*8)
    #non-linear addition to every byte
    c += int('01010101'*(block_size), 2)
    c = c & int('ff'*block_size, 16)
    #format result
    return l2b(c)


def encrypt_block(
    m: bytes,
    expanded_key: bytes, sbox_key: bytes,
    block_size: int
):
    return reduce(lambda ct, round_num:
                  encrypt_round(
                      ct,
                      expanded_key[
                          round_num*block_size:(round_num+1)*block_size
                      ],
                      sbox_key[round_num*4:(round_num+1)*4],
                      block_size
                  ),
                  range(len(expanded_key)//block_size), m
                  )


def apply_sbox_inv(b, sbox_inv):
    return b2l(bytes([sbox_inv[x] for x in l2b(b)]))


def invert_sbox(sbox_key):
    sbox = [i | (i << 4) for i in range(0x10)]
    for k in sbox_key:
        for x in sbox[:]:
            sbox.append(k ^ x)
    sbox_inv = nth(zip(*sorted(enumerate(sbox), key=lambda x: x[1])), 0)
    return bytes(sbox_inv)


def decrypt_sboxs(sbox_keys):
    return [invert_sbox(x) for x in chunks(sbox_keys, 4)]


def decrypt_round(
    c: bytes,
    key: bytes, sbox_inv: bytes,
    block_size: int
):
    m, key = b2l(c), b2l(key)
    #non-linear addition
    m = (m - int('01'*block_size*4, 2)) % (1 << (block_size*8))
    #shuffle
    mask = int('f0'*block_size, 16)
    uh, lh = m & mask, m & (mask >> 4)
    m = uh | ror(lh, 8*7, block_size*8)
    #sbox
    m = apply_sbox_inv(m, sbox_inv)
    #key
    m ^= key
    return l2b(m)


def decrypt_block(
    c: bytes,
    expanded_key: bytes, sbox_inv: bytes,
    block_size: int
):
    keys = list(chunks(expanded_key, block_size))
    return reduce(lambda pt, round_num:
                  decrypt_round(
                      pt,
                      bytes(keys[-1*round_num-1]),
                      sbox_inv[-1*round_num-1],
                      block_size
                  ),
                  range(len(expanded_key)//block_size), c
                  )


def analysis(key, diff):
    print("key: {:032x}".format(b2l(key)))
    keys, sbox = expand_key(key, 16)
    colorama.init()
    bits = [0 for _ in range(16*8)]
    sample = 5000
    for s in trange(sample):
        diff_sqrd = []
        #diff = b2l(os.urandom(16))
        x, y = b2l(os.urandom(16)), b2l(os.urandom(16))
        for i in (x, y):
            a = b2l(encrypt_block(l2b(i), keys, sbox, 16))
            b = b2l(encrypt_block(l2b(i ^ diff), keys, sbox, 16))
            diff_sqrd.append(a ^ b)
            if s == 0:
                print("\r{:032x}->{:032x}  ".format(i, a))
                print("{:032x}->{:032x}  ".format(i ^ diff, b))
                print("{:032x}->{:032x}  ".format(diff, a ^ b))
                print("-"*66)

        r = diff_sqrd[0] ^ diff_sqrd[1]
        if s == 0:
            print("{:032x}".format(r).rjust(66, ' '))
            print('\r')

        #r = encrypt_block(os.urandom(16), keys, sbox, 16)
        r = '{:0128b}'.format(r)
        bits = [x+int(y, 2) for x, y in zip(bits, r)]

    from colorama import Fore
    green, yellow, red = Fore.GREEN, Fore.YELLOW, Fore.RED
    reset = colorama.Style.RESET_ALL
    tests = []
    for x in bits:
        t = binom_test(x, sample, 0.5)
        x = "%.2E" % t
        if len(x) > 8:
            x = red+"0"*5+reset
            tests.append(x)
            continue
        x = re.sub(r"\.|E|-|\+", "", x)
        if t <= 0.1 and t >= 0.01:
            x = yellow+x+reset
        elif t < 0.01:
            x = red+x+reset
        tests.append(x)
    print("\r\nProbability that each bit is equally likely 0 or 1")
    print('format: XYYZZ = X.YYE-ZZ')
    print('\n'.join(chunks(tests, 8, m=' '.join)))
    print("Overall: ", end='')
    final = binom_test(sum(bits), sample*len(bits), 0.5)
    print((red if final <= 0.05 else green) + "%.4E" % final + reset)


def main(out, **kwargs):
    logger.debug("main(%r)", locals())

    num_ones = 2
    diff = reduce(
        lambda a, x: a | (1 << x),
        random.sample(range(16*8), num_ones),
        0
    )
    analysis(os.urandom(16), diff)


if __name__ == "__main__":
    #make the argument parser
    parser = argparse.ArgumentParser(
        description="This program implements a custom cipher.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    #call main
    main(**parse_args(parser, root_logger=False))
