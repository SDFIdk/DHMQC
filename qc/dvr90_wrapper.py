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
from __future__ import print_function

import sys
import os
import time

import numpy as np
import laspy

import dhmqc_constants as constants
from utils.osutils import ArgumentParser, run_command
from thatsDEM import grid

GEOID_GRID = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "dkgeoid13b.utm32"))

BIN_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "bin"))
DVR90 = os.path.join(BIN_DIR, "DVR90")

if sys.platform.startswith("win"):
    os.environ["PATH"] += ";" + BIN_DIR

progname = os.path.basename(__file__).replace(".pyc", ".py")
parser = ArgumentParser(
    description="Warp las/laz file from ellipsoidal heights to orthometric heights.", prog=progname)
parser.add_argument("las_file", help="input 1km las tile.")
parser.add_argument("outdir", help="Output folder.")


def usage():
    parser.print_help()


def main(args):
    t1 = time.time()
    try:
        pargs = parser.parse_args(args[1:])
    except Exception, error_msg:
        print(str(error_msg))
        return 1

    kmname = constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" % (progname, kmname, time.asctime()))
    if not os.path.exists(pargs.outdir):
        os.mkdir(pargs.outdir)

    path = pargs.las_file
    filename = os.path.basename(path)
    out_path = os.path.join(pargs.outdir, filename)

    las_in = laspy.file.File(path, mode='r')
    las_out = laspy.file.File(out_path, mode='w', header=las_in.header)

    points = las_in.points
    las_out.points = points

    xy = np.column_stack((las_in.x, las_in.y))
    geoid = grid.fromGDAL(GEOID_GRID, upcast=True)
    N = geoid.interpolate(xy)

    # Apply vertical offset from geoid grid
    las_out.z -= N

    las_in.close()
    las_out.close()

    return 0

# to be able to call the script 'stand alone'
if __name__ == "__main__":
    main(sys.argv)
