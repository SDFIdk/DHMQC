from __future__ import print_function
from __future__ import absolute_import
# Copyright (c) 2015-2016, Danish Geodata Agency <gst@gst.dk>
# Copyright (c) 2016, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
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
#
######################################################################################
##  TEMPLATE FOR A TEST TO BE WRAPPED
##  FILL IN AND DELETE BELOW...
######################################################################################
from builtins import str
import sys
import os
import time

import numpy as np

# Import some relevant modules...
from .thatsDEM import pointcloud, vector_io, array_geometry
from .db import report
from . import dhmqc_constants as constants

# If you want this script to be included in the test-suite use this subclass.
# Otherwise argparse.ArgumentParser will be the best choice :-)
# utils.osutils.Argumentparser is a simple subclass of argparse.ArgumentParser
# which raises an exception instead of using sys.exit if supplied with bad arguments...
from .utils.osutils import ArgumentParser

z_min  =  1.0
cut_to =  constants.terrain

# To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")

# Argument handling - if module has a parser attributte it will be used to check
# arguments in wrapper script.
parser   = ArgumentParser(description = "Write something here",  prog = progname)

db_group = parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local", action = "store_true", help = "Force use of local database for reporting.")
db_group.add_argument("-schema",    help = "Specify schema for PostGis db.")

# Add some arguments below
parser.add_argument("-class", type = int,   default = cut_to,  help = "Inspect points of this class - defaults to 'terrain'")
parser.add_argument("-zlim",  type = float, default = z_min,   help = "Specify the minial z-size of a steep triangle.")

group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",  help = "Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",   help = "Specify sql-statement for layer selection (e.g. for reference data in a database). "+vector_io.EXTENT_WKT +
                   " can be used as a placeholder for wkt-geometry of area of interest - in order to enable a significant speed up of db queries", type = str)

parser.add_argument("las_file",  help = "input 1km las tile.")
parser.add_argument("ref_data",  help = "input reference data connection string (e.g to a db, or just a path to a shapefile).")


# A usage function will be imported by wrapper to print usage for test.
# Otherwise ArgumentParser will handle that...
def usage():
    parser.print_help()


def main(args):
    try:
        pargs = parser.parse_args(args[1:])
    except Exception as e:
        print(str(e))
        return 1

    kmname = constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))

# To be able to call the script 'stand alone'
if __name__=="__main__":
    main(sys.argv)
