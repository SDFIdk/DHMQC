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
density_grid.py

Create a raster grid from a pointcloud where cell values indicates the number
of points inside the cell. A density grid can be created for only a subset of
the point classes within the point cloud.
'''

from __future__ import print_function

from __future__ import absolute_import
import os
import sys
import time
from .utils.osutils import ArgumentParser

import numpy as np

from . import dhmqc_constants as constants
from .thatsDEM import pointcloud

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
parser.add_argument(
    '-cls',
    help='''class number to count. Default is "all",
          otherwise valid input is a comma-separated list of class numbers,
          e.g. 0,1,2,3,7,8,10''',
    default=None,
    type=str,
)
parser.add_argument('-nd_val', help='NODATA value, defaults to 0', default=0, type=float)

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
    except TypeError as error_msg:
        print(str(error_msg))
        return 1

    lasname = pargs.las_file
    outdir = pargs.output_dir
    kmname = constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" % (PROGNAME, kmname, time.asctime()))

    try:
        xll, yll, xlr, yul = constants.tilename_to_extent(kmname)
    except (ValueError, AttributeError) as error_msg:
        print("Exception: %s" % error_msg)
        print("Bad 1km formatting of las file: %s" % lasname)
        return 1

    # Build a list of classes to includ
    classes = None
    try:
        if pargs.cls is not None:
            classes = set([int(i) for i in pargs.cls.split(',')])
    except ValueError:
        print('Ill-formed class list. Valid input is a comma-separated list of integers.')
        return 1


    o_name_grid = kmname + "_density"
    pts = pointcloud.fromLAS(lasname)
    if classes is not None:
        pts = pts.cut_to_class(classes)

    cell_size = pargs.cs
    density_grid = pts.get_grid(x1=xll, x2=xlr, y1=yll, y2=yul,
                              cx=cell_size, cy=cell_size,
                              nd_val=pargs.nd_val, method="density")

    save_path = os.path.join(outdir, o_name_grid + '.tif')

    density_grid.grid = density_grid.grid.astype(np.int32)
    rc = density_grid.save(save_path, dco=["TILED=YES", "COMPRESS=LZW"], srs=constants.srs)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
