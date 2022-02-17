# Copyright (c) 2015-2016, Danish Geodata Agency <gst@gst.dk>
# Copyright (c) 2016-2022, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
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
REMOVED - DO NOT USE - This is a stub module that only exists to raise an error
asking the user to no longer use it.
'''
import os
from qc.utils.osutils import ArgumentParser

PROGNAME = os.path.basename(__file__).replace('.pyc', '.py')

parser = ArgumentParser(
    description='''REMOVED - DO NOT USE
                   
                   Perform a range of classification modifications in one go.
                   Note that using the same disk for both reading and writing
				   may cause poor performance.''',
    prog=PROGNAME,
    )
parser.add_argument('las_file', help='input 1km las tile.')
parser.add_argument(
    'outdir',
    help='Resting place of modified input file.',
    )
# The json definition must be a list of tasks - each element must be a
# list of two elements  (name,  definition) where name is one of the valid
# tasks (see below) and definition is a relevant dict for the task (as
# above)
parser.add_argument(
    '-json_tasks',
    help='''json string/file specifying what to be done.
            Must define a list of tasks (see source).
            If not given an unmodified las file is returned.''',
    )
parser.add_argument('-olaz', action='store_true', help='Output as laz - otherwise las.')

def usage():
    '''
    Print script usage instructions
    '''
    parser.print_help()

def main(args):
    '''
    Main processing algorithm. Called either stand-alone or from qc_wrap.
    '''
    raise RuntimeError("pc_repair_man has been removed. Please update your scripts")

# to be able to call the script 'stand alone'
if __name__ == '__main__':
    main(sys.argv)
