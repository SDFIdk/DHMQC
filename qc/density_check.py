# Copyright (c) 2015-16, Danish Geodata Agency <gst@gst.dk>
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
Create density grids from las-files.
'''
from __future__ import print_function

from builtins import str
from builtins import range
import os
import sys
import time

import numpy as np
from osgeo import gdal
import laspy

from qc.thatsDEM import vector_io
from qc.db import report
from qc.utils.osutils import ArgumentParser
from . import dhmqc_constants as constants

ALL_LAKE = -2  # signal density that all is lake...
CELL_SIZE = 100.0  # 100 m cellsize in density grid
TILE_SIZE = constants.tile_size  # should be 1km tiles...
GRIDS_OUT = "density_grids"
PROGNAME = os.path.basename(__file__).replace(".pyc", ".py")
ND_VAL = -9999

parser = ArgumentParser(
    description="Write density grids of input tiles - report to db.",
    prog=PROGNAME,
)
db_group = parser.add_mutually_exclusive_group()
db_group.add_argument(
    "-use_local",
    action="store_true",
    help="Force use of local database for reporting.",
)
db_group.add_argument("-schema", help="Specify schema for PostGis db.")
parser.add_argument(
    "-cs",
    type=float,
    help="Specify cell size of grid. Default 100 m (TILE_SIZE must be divisible by cell_size)",
    default=CELL_SIZE,
)
parser.add_argument(
    "-outdir",
    help="To specify an output directory. Default is " + GRIDS_OUT + " in cwd.",
    default=GRIDS_OUT,
)
# add some arguments below
parser.add_argument(
    "-lakesql",
    help="Specify sql-statement for lake layer selection (e.g. for reference data in a database)",
)
parser.add_argument(
    "-seasql",
    help="Specify sql-statement for sea layer selection (e.g. for reference data in a database)",
)
parser.add_argument("las_file", help="input 1km las tile.")
parser.add_argument(
    "ref_data",
    help="input reference data connection string (e.g to a db, or just a path to a shapefile).",
)


def usage():
    '''
    Let qc_wrap show help for this test
    '''
    parser.print_help()


def main(args):
    '''
    Core function. Called either stand-alone or from qc_wrap.
    '''
    try:
        pargs = parser.parse_args(args[1:])
    except Exception as error_str:
        print(str(error_str))
        return 1

    kmname = constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" % (PROGNAME, kmname, time.asctime()))
    cell_size = pargs.cs
    ncols_f = TILE_SIZE / cell_size
    ncols = int(ncols_f)
    if ncols != ncols_f:
        print("TILE_SIZE: %d must be divisible by cell size..." % (TILE_SIZE))
        usage()
        return 1

    print("Using cell size: %.2f" % cell_size)
    use_local = pargs.use_local
    if pargs.schema is not None:
        report.set_schema(pargs.schema)

    reporter = report.ReportDensity(use_local)
    outdir = pargs.outdir

    if not os.path.exists(outdir):
        os.mkdir(outdir)

    lasname = pargs.las_file
    waterconnection = pargs.ref_data
    outname_base = "den_{0:.0f}_".format(
        cell_size) + os.path.splitext(os.path.basename(lasname))[0] + ".tif"
    outname = os.path.join(outdir, outname_base)
    print("Reading %s, writing %s" % (lasname, outname))

    try:
        (x_min, y_min, x_max, y_max) = constants.tilename_to_extent(kmname)
    except Exception as error_str:
        print("Exception: %s" % str(error_str))
        print("Bad 1km formatting of las file: %s" % lasname)
        return 1

    las_file = laspy.read(lasname)

    nx = int((x_max - x_min) / cell_size)
    ny = int((y_max - y_min) / cell_size)
    ds_grid = gdal.GetDriverByName('GTiff').Create(outname, nx, ny, 1, gdal.GDT_Float32)
    georef = (x_min, cell_size, 0, y_max, 0, -cell_size)
    ds_grid.SetGeoTransform(georef)
    band = ds_grid.GetRasterBand(1)
    band.SetNoDataValue(ND_VAL)

    # make local copies so we don't have to call the x and y getter functions
    # of las_file a nx*ny times
    xs = las_file.x
    ys = las_file.y

    # determine densities
    den_grid = np.ndarray(shape=(nx, ny), dtype=float)
    for i in range(nx):
        for j in range(ny):
            I = np.ones(las_file.header.point_count, dtype=bool)

            if i < nx-1:
                I &= np.logical_and(xs >= x_min+i*cell_size, xs < x_min+(i+1)*cell_size)
            else:
                I &= np.logical_and(xs >= x_min+i*cell_size, xs <= x_min+(i+1)*cell_size)

            if j < ny-1:
                I &= np.logical_and(ys >= y_min+j*cell_size, ys < y_min+(j+1)*cell_size)
            else:
                I &= np.logical_and(ys >= y_min+j*cell_size, ys <= y_min+(j+1)*cell_size)

            den_grid[ny-j-1][i] = np.sum(I) / (cell_size*cell_size)

    band.WriteArray(den_grid)

    t1 = time.process_time()
    if pargs.lakesql is None and pargs.seasql is None:
        print('No layer selection specified!')
        print('Assuming that all water polys are in first layer of connection...')
        lake_mask = vector_io.burn_vector_layer(
            waterconnection,
            georef,
            den_grid.shape,
            None,
            None,
        )
    else:
        lake_mask = np.zeros(den_grid.shape, dtype=np.bool_)
        if pargs.lakesql is not None:
            print("Burning lakes...")
            lake_mask |= vector_io.burn_vector_layer(
                waterconnection,
                georef,
                den_grid.shape,
                None,
                pargs.lakesql,
            )
        if pargs.seasql is not None:
            print("Burning sea...")
            lake_mask |= vector_io.burn_vector_layer(
                waterconnection,
                georef,
                den_grid.shape,
                None,
                pargs.seasql,
            )

    t2 = time.process_time()
    print("Burning 'water' took: %.3f s" % (t2 - t1))

    # what to do with nodata??
    nd_mask = (den_grid == ND_VAL)
    den_grid[den_grid == ND_VAL] = 0
    n_lake = lake_mask.sum()
    print("Number of no-data densities: %d" % (nd_mask.sum()))
    print("Number of water cells       : %d" % (n_lake))
    if n_lake < den_grid.size:
        not_lake = den_grid[np.logical_not(lake_mask)]
        den = not_lake.min()
        mean_den = not_lake.mean()
    else:
        den = ALL_LAKE
        mean_den = ALL_LAKE
    print("Minumum density            : %.2f" % den)

    wkt = constants.tilename_to_extent(kmname, return_wkt=True)
    reporter.report(kmname, den, mean_den, cell_size, wkt_geom=wkt)

    return 0


if __name__ == "__main__":
    main(sys.argv)
