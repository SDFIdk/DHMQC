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
Delta check: check for steepnes along roads to find terrain classification failures.
Work in progress...
'''

from __future__ import print_function

from __future__ import absolute_import
import sys
import os
import time
import numpy as np

from qc.thatsDEM import pointcloud, vector_io, array_geometry
from qc.db import report
from . import dhmqc_constants as constants
from qc.utils.osutils import ArgumentParser

PROGNAME = os.path.basename(__file__)
LINE_BUFFER = 1.0

# LIMITS FOR STEEP TRIANGLES... will also imply limits for angles...
XY_MAX = 1.5  # flag triangles larger than this as invalid
Z_MIN = 0.4

# pylint: disable=invalid-name
parser = ArgumentParser(description="Check for steepnes along road center lines.", prog=PROGNAME)
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
    default=constants.terrain,
    help="Inspect points of this class - defaults to 'terrain'")
parser.add_argument(
    "-zlim",
    dest="zlim",
    type=float,
    default=Z_MIN,
    help="Specify the minial z-size of a steep triangle.")
parser.add_argument("-runid", dest="runid", help="Set run id for the database...")
layer_group = parser.add_mutually_exclusive_group()
layer_group.add_argument(
    "-layername",
    help="Specify layername (e.g. for reference data in a database)")
layer_group.add_argument(
    "-layersql",
    help="Specify sql-statement for layer selection (e.g. for reference data in a database)",
    type=str)
parser.add_argument("las_file", help="input 1km las tile.")
parser.add_argument("lines", help="input reference road lines.")
# pylint: enable=invalid-name

def usage():
    '''
    Print help from argparser
    '''
    parser.print_help()


def main(args):
    '''
    Run road delta check. Invoked from either command line or qc_wrap.py
    '''
    pargs = parser.parse_args(args[1:])
    lasname = pargs.las_file
    linename = pargs.lines
    kmname = constants.get_tilename(lasname)
    print("Running %s on block: %s, %s" % (os.path.basename(args[0]), kmname, time.asctime()))
    if pargs.schema is not None:
        report.set_schema(pargs.schema)
    reporter = report.ReportDeltaRoads(pargs.use_local)
    cut_class = pargs.cut_class
    pc = pointcloud.fromAny(lasname).cut_to_class(cut_class)
    if pc.get_size() < 5:
        print("Too few points to bother..")
        return 1

    pc.triangulate()
    geom = pc.get_triangle_geometry()
    print("Using z-steepnes limit {0:.2f} m".format(pargs.zlim))
    mask = np.logical_and(geom[:, 1] < XY_MAX, geom[:, 2] > pargs.zlim)
    geom = geom[mask]  # save for reporting
    if not mask.any():
        print("No steep triangles found...")
        return 0

    # only the centers of the interesting triangles
    centers = pc.triangulation.get_triangle_centers()[mask]
    print("{0:d} steep triangles in tile.".format(centers.shape[0]))
    try:
        extent = np.asarray(constants.tilename_to_extent(kmname))
    except Exception:
        print("Could not get extent from tilename.")
        extent = None

    lines = vector_io.get_geometries(linename, pargs.layername, pargs.layersql, extent)
    feature_count = 0
    for line in lines:
        xy = array_geometry.ogrline2array(line, flatten=True)
        if xy.shape[0] == 0:
            print("Seemingly an unsupported geometry...")
            continue

        # select the triangle centers which lie within line_buffer of the road segment
        mask = array_geometry.points_in_buffer(centers, xy, LINE_BUFFER)
        critical = centers[mask]

        print("*" * 50)
        print("{0:d} steep centers along line {1:d}".format(critical.shape[0], feature_count))
        feature_count += 1

        if critical.shape[0] > 0:
            z_box = geom[mask][:, 2]
            z1 = z_box.max()
            z2 = z_box.min()
            wkt = "MULTIPOINT("
            for point in critical:
                wkt += "{0:.2f} {1:.2f},".format(point[0], point[1])
            wkt = wkt[:-1] + ")"
            reporter.report(kmname, z1, z2, wkt_geom=wkt)


if __name__ == "__main__":
    main(sys.argv)
