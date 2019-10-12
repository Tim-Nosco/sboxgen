#!/usr/bin/env python3
from common import hook, parse_args, fatal
import argparse, logging
logger = logging.getLogger(__name__)

def main(out, **kwargs):
    logger.debug("main(%r)", locals())

    
if __name__ == "__main__":
    #make the argument parser
    parser = argparse.ArgumentParser(
        description="This program will generate a differential "
            "cryptanalysis resistant sbox."
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    #call main
    main(**parse_args(parser, root_logger=False))
