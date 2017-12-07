# Copyright (c) 2017, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

'''
main.py

Entry point for the dhmqc command line interface.
'''

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import sys
import argparse

import dhmqc
from dhmqc.apps import tindex

HELP_TEXT = '''DHMQC v. {0}

Usage:

    dhmqc <subcommand> <options>

Sub commands:

    tindex
'''.format(dhmqc.__version__)

def main():

    sys.argv

    if len(sys.argv) <= 1:
        print(HELP_TEXT)
        return 1

    if sys.argv[1] == 'tindex':
        parser = tindex.setup_parser()
        args = parser.parse_args(sys.argv[2:])
    elif sys.argv[1] == 'db':
        print('db')
    else:
        print(HELP_TEXT)
        return 1

    args.func(args)


if __name__ == '__main__':
    main()
