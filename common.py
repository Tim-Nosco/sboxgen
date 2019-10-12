#!/usr/bin/env python3

import argparse,logging,inspect,sys

logger = logging.getLogger(__name__)
fmt = "\r%(levelname)08s:%(filename)s:%(lineno)04d:%(message)s"

def hook():
    #allow the caller to update the local and global dicts
    locals().update(inspect.stack()[1].frame.f_locals)
    #create interactive shell
    import IPython
    IPython.embed(confirm_exit=False,banner1="")
    logger.fatal("Exiting")
    exit(0)

def fatal(**args):
    #simple log/exit chain
    logger.fatal(**args)
    logger.fatal("Exiting")
    exit(0)

def parse_args(parser, root_logger=False):
    #add the log level as an argument
    levels = [x for x,_ in sorted(
        logging._nameToLevel.items(),key=lambda x: x[1]
    )]
    parser.add_argument("--log-level", "-v", default=levels[0],
        help="Select the amount of logging.",
        choices=levels
    )
    #output file
    parser.add_argument("--output", "-o", default=sys.stdout,
        type=argparse.FileType('w'), action="store",
        dest="out",
        help="Specify the location to write the program's output. "
             "Does not include logging.",
    )
    #parse arguments
    args = parser.parse_args()
    #determine the numerical level
    log_level = logging._nameToLevel[args.log_level]
    #it can be convienent to specify the log level of all 
    # modules in one place. It can be noisy, however.
    if root_logger:
        #adding a handler to this logger will affect all other loggers
        logger = logging.getLogger()
    else:
        #create the logger with a name matching the calling 
        # function's module name
        logger = logging.getLogger(
            inspect.stack()[1].frame.f_globals['__name__']
        )
    #create console handler
    ch = logging.StreamHandler()
    #specify the logging format
    ch.setFormatter(logging.Formatter(fmt))
    ch.setLevel(log_level)
    #register handler with the logger
    logger.addHandler(ch)
    #set the level
    logger.setLevel(log_level)
    #Turn arguments into a dictionary for use with the "**" unpacker
    return dict(args._get_kwargs())
