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
Count classes in a point cloud.
'''

from __future__ import print_function

from builtins import str
import sys
import os
import time

from . import dhmqc_constants as constants
from qc.thatsDEM import pointcloud
from qc.db import report
from qc.dhmqc_constants import get_tilename
from qc.dhmqc_constants import tilename_to_extent
from qc.utils.osutils import ArgumentParser

PROGNAME = os.path.basename(__file__).replace(".pyc", ".py")

parser = ArgumentParser(
    description="Count points per class in a tile",
    prog=PROGNAME)

db_group = parser.add_mutually_exclusive_group()
db_group.add_argument(
    "-use_local",
    action="store_true",
    help="Force use of local database for reporting.")
db_group.add_argument("-schema", help="Specify schema for PostGis db.")

parser.add_argument("las_file", help="input las tile.")


def usage():
    '''
    Print help text from argument parser.
    '''
    parser.print_help()


def main(args):
    '''
    Main script functionality. Can be invoked from either the command line
    or via qc_wrap.py
    '''

    try:
        pargs = parser.parse_args(args[1:])
    except Exception as error_msg:
        print(str(error_msg))
        return 1

    kmname = get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" % (PROGNAME, kmname, time.asctime()))
    if pargs.schema is not None:
        report.set_schema(pargs.schema)
    reporter = report.ReportClassCount(pargs.use_local)
    pc = pointcloud.fromAny(pargs.las_file)
    n_points_total = pc.get_size()
    if n_points_total == 0:
        print("Something is terribly terribly wrong here! Simon - vi skal melde en fjel")

    pc_temp = pc.cut_to_class(constants.created_unused)
    n_created_unused = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.surface)
    n_surface = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.terrain)
    n_terrain = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.low_veg)
    n_low_veg = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.high_veg)
    n_high_veg = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.med_veg)
    n_med_veg = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.building)
    n_building = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.outliers)
    n_outliers = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.mod_key)
    n_mod_key = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.water)
    n_water = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.ignored)
    n_ignored = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.bridge)
    n_bridge = pc_temp.get_size()

    # new classes
    pc_temp = pc.cut_to_class(constants.high_noise)
    n_high_noise = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.power_line)
    n_power_line = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.terrain_in_buildings)
    n_terrain_in_buildings = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.low_veg_in_buildings)
    n_low_veg_in_buildings = pc_temp.get_size()

    pc_temp = pc.cut_to_class(constants.man_excl)
    n_man_excl = pc_temp.get_size()

    polywkt = tilename_to_extent(kmname, return_wkt=True)
    print(polywkt)

    reporter.report(
        kmname,
        n_created_unused,
        n_surface,
        n_terrain,
        n_low_veg,
        n_med_veg,
        n_high_veg,
        n_building,
        n_outliers,
        n_mod_key,
        n_water,
        n_ignored,
        n_power_line,
        n_bridge,
        n_high_noise,
        n_terrain_in_buildings,
        n_low_veg_in_buildings,
        n_man_excl,
        n_points_total,
        wkt_geom=polywkt)

if __name__ == "__main__":
    main(sys.argv)
