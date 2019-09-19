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
'''
Spike check: Check for steep somewhat isolated triangles.
'''
from __future__ import print_function

import sys
import os
import time
import numpy as np

from qc.thatsDEM import pointcloud
from qc.db import report
from . import dhmqc_constants as constants
from qc.utils.osutils import ArgumentParser

CUT_TO = constants.terrain  # default to terrain only...
SLOPE_MIN = 25  # minumum this in degrees
ZLIM = 0.1  # minimum this in meters
FILTER_RAD = 1.5

# To always get the proper name in usage / help - even when called from a wrapper...
PROGNAME = os.path.basename(__file__)

parser = ArgumentParser(
    description='''Check for spikes - a spike is a point with steep edges in all four
                   quadrants (all edges should be steep unless those 'close').''',
    prog=PROGNAME)
db_group = parser.add_mutually_exclusive_group()
db_group.add_argument(
    "-use_local",
    action="store_true",
    help="Force use of local database for reporting.")
db_group.add_argument("-schema", help="Specify schema for PostGis db.")
parser.add_argument(
    "-class",
    dest="cut_class",
    type=int,
    default=CUT_TO,
    help="Inspect points of this class - defaults to 'terrain'")
parser.add_argument(
    "-slope",
    dest="slope",
    type=float,
    default=SLOPE_MIN,
    help='''Specify the minial slope in degrees of a steep edge
            (0-90 deg) - default 25 deg.''')
parser.add_argument(
    "-zlim",
    dest="zlim",
    type=float,
    default=ZLIM,
    help="Specify the minial (positive) delta z of a steep edge - default 0.1 m")
parser.add_argument("las_file", help="input 1km las tile.")


def usage():
    '''
    Print help from argparser
    '''
    parser.print_help()


def main(args):
    '''
    Main function, invoked from either command line or qc_wrap
    '''
    pargs = parser.parse_args(args[1:])
    lasname = pargs.las_file
    kmname = constants.get_tilename(lasname)
    msg = "Running %s on block: %s, %s"
    print(msg % (os.path.basename(args[0]), kmname, time.asctime()))

    if pargs.schema is not None:
        report.set_schema(pargs.schema)
    reporter = report.ReportSpikes(pargs.use_local)

    if pargs.zlim < 0:
        print("zlim must be positive!")
        usage()

    if pargs.slope < 0 or pargs.slope >= 90:
        print("Specify a slope angle in the range 0->90 degrees.")
        usage()

    cut_class = pargs.cut_class
    print("Cutting to class (terrain) {0:d}".format(cut_class))
    pc = pointcloud.fromAny(lasname).cut_to_class(cut_class)
    if pc.get_size() < 10:
        print("Too few points in pointcloud.")
        return

    print("Sorting spatially...")
    pc.sort_spatially(FILTER_RAD)
    slope_arg = np.tan(np.radians(pargs.slope))**2
    msg = "Using steepnes parameters: angle: {0:.2f} degrees, delta-z: {1:.2f}"
    print(msg.format(pargs.slope, pargs.zlim))
    print("Filtering, radius: {0:.2f}".format(FILTER_RAD))
    dz = pc.spike_filter(FILTER_RAD, slope_arg, pargs.zlim)
    mask = (dz != 0)
    dz = dz[mask]
    pc = pc.cut(mask)
    print("Spikes: {0:d}".format(mask.sum()))
    for i in range(pc.size):
        x, y = pc.xy[i]
        z = pc.z[i]
        mdz = dz[i]
        c = pc.c[i]
        pid = pc.pid[i]
        print("spike: x: {0:.2f} y: {1:.2f} mean-dz: {2:.2f}".format(x, y, mdz))
        wkt_geom = "POINT({0:.2f} {1:.2f})".format(x, y)
        reporter.report(kmname, FILTER_RAD, mdz, x, y, z, c, pid, wkt_geom=wkt_geom)


if __name__ == "__main__":
    main(sys.argv)
