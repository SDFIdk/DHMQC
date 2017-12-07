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

'''
class_grid.py

Create a raster grid from a pointcloud where cell values indicates the most frequent
class inside that cell.
'''

from __future__ import print_function

import os
import sys
import time
from utils.osutils import ArgumentParser

import dhmqc_constants as constants
from thatsDEM import pointcloud

CELL_SIZE = 1.0
PROGNAME = os.path.basename(__file__).replace(".pyc", ".py")

parser = ArgumentParser(
    description="Write a grid with cells representing most frequent class.",
    prog=PROGNAME)
parser.add_argument("las_file", help="Input las tile.")
parser.add_argument("output_dir", help="output directory of class grids.")
parser.add_argument(
    "-cs",
    type=float,
    help="Cellsize (defaults to {0:.2f})".format(CELL_SIZE),
    default=CELL_SIZE)

def usage():
    '''
    Print usage
    '''
    parser.print_help()

def main(args):
    '''
    Main function
    '''
    try:
        pargs = parser.parse_args(args[1:])
    except TypeError, error_msg:
        print(str(error_msg))
        return 1
    lasname = pargs.las_file
    outdir = pargs.output_dir
    kmname = constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" % (PROGNAME, kmname, time.asctime()))
    try:
        xll, yll, xlr, yul = constants.tilename_to_extent(kmname)
    except (ValueError, AttributeError), error_msg:
        print("Exception: %s" % error_msg)
        print("Bad 1km formatting of las file: %s" % lasname)
        return 1
    o_name_grid = kmname + "_class"
    pts = pointcloud.fromAny(lasname) #terrain subset of surf so read filtered...
    print("Gridding classes...")
    cell_size = pargs.cs
    class_grid = pts.get_grid(x1=xll, x2=xlr, y1=yll, y2=yul,
                              cx=cell_size, cy=cell_size, method="class")
    save_path = os.path.join(outdir, o_name_grid + '.tif')
    class_grid.save(save_path, dco=["TILED=YES", "COMPRESS=LZW"], srs=constants.srs)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
