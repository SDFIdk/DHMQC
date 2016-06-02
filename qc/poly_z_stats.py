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
Calculate statistics on the vertical component within polygons.
'''
from __future__ import print_function

import sys
import os
import time
import numpy as np

import dhmqc_constants as constants
from thatsDEM import pointcloud
from thatsDEM import vector_io
from thatsDEM import array_geometry
from thatsDEM import grid
from db import report
from utils.osutils import ArgumentParser


#z_min = 1.0
CUT_TO = constants.building

# Path to geoid grid
GEOID_GRID = os.path.join(os.path.dirname(__file__), "..", "data", "dkgeoid13b_utm32.tif")
# To always get the proper name in usage / help - even when called from a wrapper...
PROGNAME = os.path.basename(__file__).replace(".pyc", ".py")

parser = ArgumentParser(
    description="Report height statistics for a specific class in polygons",
    prog=PROGNAME)

db_group = parser.add_mutually_exclusive_group()
db_group.add_argument(
    "-use_local",
    action="store_true",
    help="Force use of local database for reporting.")

db_group.add_argument(
    "-schema",
    help="Specify schema for PostGis db.")

parser.add_argument(
    "-class",
    type=int,
    default=CUT_TO,
    dest="ccut",
    help="Inspect points of this class - defaults to 'building'")

parser.add_argument(
    "-nowarp",
    action="store_true",
    help='''Pointcloud is already in dvr90 - so do not warp.
            Default is to assume input is in ellipsoidal heights.''')

layer_group = parser.add_mutually_exclusive_group()
layer_group.add_argument(
    "-layername",
    help="Specify layername (e.g. for reference data in a database)")

layer_group.add_argument(
    "-layersql",
    help='''Specify sql-statement for layer selection
            (e.g. for reference data in a database).
            {wkt_placeholder} can be used as a placeholder for wkt-geometry of area of interest
            in order to enable a significant speed up of db queries.
         '''.format(wkt_placeholder=vector_io.EXTENT_WKT),
    type=str)

parser.add_argument("las_file", help="input 1km las tile.")

parser.add_argument(
    "poly_ds",
    help="input reference data connection string (e.g to a db, or just a path to a shapefile).")


def usage():
    parser.print_help()


def main(args):
    try:
        pargs = parser.parse_args(args[1:])
    except Exception, error_msg:
        print(str(error_msg))
        return 1

    kmname = constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" % (PROGNAME, kmname, time.asctime()))

    extent = np.asarray(constants.tilename_to_extent(kmname))
    reporter = report.ReportZStatsInPolygon(pargs.use_local)
    polys = vector_io.get_geometries(pargs.poly_ds, pargs.layername, pargs.layersql, extent)
    print("Number of polygons: %d" % len(polys))

    if len(polys) == 0:
        return 3

    pc = pointcloud.fromAny(pargs.las_file).cut_to_class(pargs.ccut)
    print("Number of points of class %s: %d" % (str(pargs.ccut), pc.size))

    if not pargs.nowarp:
        # Warp to dvr90 if needed (default)
        geoid = grid.fromGDAL(GEOID_GRID, upcast=True)
        pc.toH(geoid)
        del geoid

    for poly in polys:
        arr = array_geometry.ogrpoly2array(poly, flatten=True)
        pc_in_poly = pc.cut_to_polygon(arr)
        n_points = pc_in_poly.size
        if pc_in_poly.size > 0:
            z_min = pc_in_poly.z.min()
            z_max = pc_in_poly.z.max()
            z_mean = pc_in_poly.z.mean()
            z_stddev = np.std(pc_in_poly.z)
            z_5percentile = np.percentile(pc_in_poly.z, 5)
        else:
            z_min = 0
            z_max = 0
            z_mean = 0
            z_stddev = 0
            z_5percentile = 0
        reporter.report(
            kmname,
            pargs.ccut,
            n_points,
            z_min,
            z_max,
            z_mean,
            z_stddev,
            z_5percentile,
            ogr_geom=poly)


if __name__ == "__main__":
    # to be able to call the script 'stand alone'
    main(sys.argv)
