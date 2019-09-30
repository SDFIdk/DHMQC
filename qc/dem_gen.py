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
dem_gen_new.py

Generate DTMs and DSMs from a pointcloud using supporting vector data.
'''
from __future__ import print_function

from builtins import str
import sys
import os
import json
from argparse import ArgumentParser
from math import ceil
from math import modf

import numpy as np
import scipy.ndimage as image
from osgeo import osr
from osgeo import ogr

from . import dhmqc_constants as constants
from qc.thatsDEM import pointcloud
from qc.thatsDEM import grid
from qc.thatsDEM import array_geometry
from qc.thatsDEM import vector_io

GEOID_GRID = os.path.join(os.path.dirname(__file__), "..", "data", "dkgeoid13b_utm32.tif")

CELL_SIZE = 0.4
BUFBUF = 200

# buffer with this amount of cells... should be larger than various smoothing radii
# and BUFBUF>CELL_BUF*pargs.cell_size
CELL_BUF = 20
SYNTH_TERRAIN = 2
EPSG_CODE = 25832
SRS = osr.SpatialReference()
SRS.ImportFromEPSG(EPSG_CODE)
SRS_WKT = SRS.ExportToWkt()
SRS_PROJ4 = SRS.ExportToProj4()
TIF_CREATION_OPTIONS = ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3", "ZLEVEL=9"]

# Constants that can be changed via CLI
Z_LIMIT = 1.0 # for steep triangles towards water...
ND_VAL = -9999
DSM_TRIANGLE_LIMIT = 3 #LIMIT for large triangles
H_SYS = "E" #default H_SYS - can be changed...
SEA_TOLERANCE = 0.8  #this much away from sea_z or mean or something aint sea...
LAKE_TOLERANCE = 0.45 #this much higher than lake_z is deemed not lake!

#TILE_COVERAGE DEFAULTS:
ROW_COL_SQL = "SELECT row, col FROM coverage WHERE tile_name='{TILE_NAME}'"
TILE_SQL = """SELECT
                path,
                '2,9,17' as gcls,
                '2,3,4,5,6,9,17' as scls,
                'E' as hsys
              FROM
                coverage
              WHERE
                abs(({ROW})-row)<2 AND abs(({COL})-col)<2"""

parser = ArgumentParser(
    prog=os.path.basename(__file__),
    description="Generate DTM for a las file. Will try to read surrounding tiles for buffer.")
parser.add_argument(
    "-cell_size",
    type=float,
    default=CELL_SIZE,
    help='Cell size of generated tif-files. Defaults to %.2f m' % CELL_SIZE,
)
parser.add_argument(
    "-overwrite",
    action="store_true",
    help="Overwrite output file if it exists. Default is to skip the tile.")
parser.add_argument(
    "-dsm",
    action="store_true",
    help="Also generate a dsm.")
parser.add_argument(
    "-dtm",
    action="store_true",
    help="Generate a dtm.")
parser.add_argument(
    "-triangle_limit",
    type=float,
    help="""Specify triangle size limit in DSM for when to not render (and fill in from DTM.)
             (defaults to %.2f m)""" % DSM_TRIANGLE_LIMIT,
    default=DSM_TRIANGLE_LIMIT)
parser.add_argument(
    "-zlim",
    type=float,
    help="Limit for when a large wet triangle is not flat",
    default=Z_LIMIT)
parser.add_argument(
    "-hsys",
    choices=["dvr90", "E"],
    default="dvr90",
    help="Output height system (E or dvr90 - default is dvr90).")
parser.add_argument(
    "-nowarp",
    action="store_true",
    help="Do not change height system - assume same for all input tiles")
parser.add_argument(
    "-debug",
    action="store_true",
    help="Debug - save some additional metadata grids.")
parser.add_argument(
    "-round",
    action="store_true",
    help="Round to mm level (experimental)")
parser.add_argument(
    "-flatten",
    action="store_true",
    help="Flatten water (experimental - will require a buffered dem)")
parser.add_argument(
    "-smooth_rad",
    type=int,
    help="Specify a positive radius to smooth large (dry) triangles (below houses etc.)",
    default=0)
parser.add_argument(
    "-clean_buildings",
    action="store_true",
    help="Remove terrain pts in buildings.")
parser.add_argument(
    "-lake_tolerance_dtm",
    type=float,
    default=LAKE_TOLERANCE,
    help="""Specify tolerance for how much something may be higher than
            in order to be deemed as water. Deafults to: %.2f m""" % LAKE_TOLERANCE)
parser.add_argument(
    "-lake_tolerance_dsm",
    type=float,
    default=LAKE_TOLERANCE,
    help="""Specify tolerance for how much something may be higher than
            in order to be deemed as water. Deafults to: %.2f m""" % LAKE_TOLERANCE)
parser.add_argument(
    "-sea_tolerance",
    type=float,
    default=SEA_TOLERANCE,
    help="""Specify tolerance for how much something may be higher than sea_z
            in order to be deemed as sea. Deafults to: %.2f m""" % SEA_TOLERANCE)
parser.add_argument(
    "-sea_z",
    type=float,
    default=0,
    help="Burn this value into sea (if given) - defaults to 0.")
parser.add_argument(
    "-burn_sea",
    action="store_true",
    help="Burn a constant (sea_z) into sea (if specified).")
parser.add_argument(
    "-layer_def",
    help="""Input json-parameter file / json-parameter string specifying connections
             to reference layers. Can be set to 'null' - meaning ref-layers will not be used.""")
parser.add_argument(
    "-rowcol_sql",
    help="""SQL which defines how to select row,col given tile_name.
             Must contain the token {TILE_NAME} for replacement.""",
    default=ROW_COL_SQL,
    type=str)
parser.add_argument(
    "-tile_sql",
    help="""SQL which defines how to select path, ground_classes, surface_classes,
            height_system for neighbouring tiles given row and column.
            Must contain tokens {ROW} and {COL} for replacement.""",
    default=TILE_SQL,
    type=str)
parser.add_argument(
    "-remove_bridges_in_dtm",
    action="store_true",
    help="""Discard points of class 17 (bridge decks) when computing DTM.""")
parser.add_argument(
    "-no_expand_water",
    action="store_true",
    help="""Do not expand water mask.""")
parser.add_argument(
    "las_file",
    help="Input las tile (the important bit is tile name).")
parser.add_argument(
    "tile_cstr",
    help="OGR connection string to a tile db.")
parser.add_argument(
    "output_dir",
    help="Where to store the dems e.g. c:\\final_resting_place\\")

def usage():
    '''Print help text on screen.'''
    parser.print_help()


def expand_water(add_mask, water_mask, element=None, verbose=False):
    '''
    Expand water mask by identifying coherent features in add_mask
    that crosses water boundaries. Features that cross water boundaries
    are assumed to be water and the water_mask is expanded so it covers
    those features.

    Arguments:
        add_mask:           Input mask from which features are identified.
        water_mask:         Water mask.
        element:            A structuring element that defines feature connections.
                            Structure must be symmetric.
        verbose:            Print extra info.

    Returns:
        expanded water_mask
    '''
    labeled_features, _ = image.measurements.label(add_mask, element)

    #take components of add_mask which both intersects water_mask and its complement
    in_water = np.unique(labeled_features[water_mask])
    outside_water = np.unique(labeled_features[np.logical_not(water_mask)])
    inside_outside = set(in_water).intersection(set(outside_water))
    if verbose:
        print("Number of components to do: %d" % len(inside_outside))
        print("Cells before expansion: %d" % water_mask.sum())
    for i in inside_outside:
        if i > 0:
            water_mask |= (labeled_features == i)

    #do some more morphology to lake_mask and dats it
    if verbose:
        print("Cells after expansion: %d" % water_mask.sum())
    return water_mask

def gridit(points, extent, cell_size, g_warp=None, doround=False):
    '''
    Grid pointcloud within extent.

    Arguments:
        points:         thatsDEM pointcloud object.
        extent:             Extent of output grid. Must be on the form [xmin, ymin, xmax, ymax].
        cell_size:          Cell size of grid.
        g_warp:             Height transformation grid. Typically a geoid grid.
        doround:            Rounds grid-values to 3 decimals.

    Returns:
        grid:               thatsDEM.grid.Grid object with heights in each grid cell.
        triangles:          thatsDEM.grid.Grid object with triangle sizes in grid cells.
                            Can be used to identify individual triangles in the grid.
    '''
    if points.triangulation is None:
        points.triangulate()

    triangulated_grid, triangles = points.get_grid(
        x1=extent[0],
        x2=extent[2],
        y1=extent[1],
        y2=extent[3],
        cx=cell_size,
        cy=cell_size,
        nd_val=ND_VAL,
        method="return_triangles")

    mask = (triangulated_grid.grid != ND_VAL)
    if not mask.any():
        return None, None

    if g_warp is not None:
        #warp heights with warp-grid
        triangulated_grid.grid[mask] -= g_warp[mask]

    triangulated_grid.grid = triangulated_grid.grid.astype(np.float32)
    triangles.grid = triangles.grid.astype(np.float32)

    if doround:
        # Experimental feature
        grid.grid = np.around(grid.grid, 3)

    return triangulated_grid, triangles


def get_neighbours(connection_str, tilename, rowcol_sql, tile_sql, remove_bridges_in_dtm=False):
    '''
    Get neighbouring tiles.

    Default neighbour getter - using a tiledb like tile_coverage.py
    '''
    datasource = ogr.Open(connection_str)
    rowcol_sql = rowcol_sql.format(TILE_NAME=tilename)
    layer = datasource.ExecuteSQL(str(rowcol_sql))

    if layer is None or layer.GetFeatureCount() != 1:
        raise Exception("Did not select exactly one feature using SQL: " + rowcol_sql)

    feat = layer.GetNextFeature()
    row = feat.GetFieldAsInteger(0)
    col = feat.GetFieldAsInteger(1)
    datasource.ReleaseResultSet(layer)
    tile_sql = tile_sql.format(ROW=row, COL=col)
    layer = datasource.ExecuteSQL(str(tile_sql))

    if layer is None or layer.GetFeatureCount() < 1:
        raise Exception("Did not select at least one feature using SQL: " + tile_sql)

    data = []
    for feat in layer:
        path = feat.GetFieldAsString(0)
        #gr_cls = map(int, feat.GetFieldAsString(1).split(","))
        if remove_bridges_in_dtm:
            gr_cls = [int(cls) for cls in feat.GetFieldAsString(1).split(',') if int(cls) != 17]
        else:
            gr_cls = [int(cls) for cls in feat.GetFieldAsString(1).split(',')]
        #surf_cls = map(int, feat.GetFieldAsString(2).split(","))
        surf_cls = [int(cls) for cls in feat.GetFieldAsString(2).split(',')]
        h_sys = feat.GetFieldAsString(3)
        data.append((path, gr_cls, surf_cls, h_sys))
    datasource.ReleaseResultSet(layer)
    layer = None
    datasource = None

    return data

def setup_masks(fargs, nrows, ncols, georef):
    '''
    Set up masks for water and buildings

    Arguments:
        fargs:          Arguments from layer definitions.
        nrows:          Number of row in masks.
        ncols:          Number of columns in masks.
        georef:     Georeference for masks.

    Returns:
        water_mask, lake_mask, sea_mask and build_mask
    '''
    water_mask = np.zeros((nrows, ncols), dtype=np.bool)
    lake_raster = None
    sea_mask = None
    build_mask = None

    if fargs["LAKE_LAYER"] is not None:
        map_cstr, sql = fargs["LAKE_LAYER"]
        water_mask |= vector_io.burn_vector_layer(
            map_cstr,
            georef,
            (nrows, ncols),
            layersql=sql)

    if fargs["LAKE_Z_LAYER"] is not None:
        map_cstr, sql = fargs["LAKE_Z_LAYER"]
        lake_raster = vector_io.burn_vector_layer(
            map_cstr,
            georef,
            (nrows, ncols),
            layersql=sql,
            nd_val=ND_VAL,
            attr=fargs["LAKE_Z_ATTR"],
            dtype=np.float32)

    if fargs["RIVER_LAYER"] is not None:
        map_cstr, sql = fargs["RIVER_LAYER"]
        water_mask |= vector_io.burn_vector_layer(
            map_cstr,
            georef,
            (nrows, ncols),
            layersql=sql)

    if fargs["SEA_LAYER"] is not None:
        map_cstr, sql = fargs["SEA_LAYER"]
        sea_mask = vector_io.burn_vector_layer(
            map_cstr,
            georef,
            (nrows, ncols),
            layersql=sql)
        water_mask |= sea_mask

    if fargs["BUILD_LAYER"] is not None:
        map_cstr, sql = fargs["BUILD_LAYER"]
        build_mask = vector_io.burn_vector_layer(
            map_cstr,
            georef,
            (nrows, ncols),
            layersql=sql)

    return water_mask, lake_raster, sea_mask, build_mask

def burn_sea(dem, sea_mask, triangle_mask, sea_z, tolerance):
    '''
    Burn sea into DEM.

    Something is sea if its in sea_mask AND not too far from sea_z OR in large
    triangle.

    Arguments:
        dem:                thatsDEM.grid.Grid object with either a DTM or DSM
        sea_mask:           Mask telling us where the sea is.
        triangle_mask:      Mask showing us where there are large triangles.
        sea_z:              Absolute height of the sea.
        tolerance:          Anything lower than this is interpreted as the sea.

    Returns:
        dem with the sea burned in.
    '''
    # Unsolved issue:
    #   Handle waves and tides somehow - I guess diff from sea_z should be less
    #   than some number AND diff from mean should be less than some smaller
    #   number (local tide),

    # Not much higher than sea - lower is OK (low tides - since ND_VAL is
    # probably really low this should give nd_values also).
    mask = (dem.grid-sea_z) < tolerance

    # Add large triangles
    mask |= triangle_mask

    # Add no-data
    mask |= (dem.grid == ND_VAL)

    # Restrict to sea mask
    mask &= sea_mask

    # Expand sea. flood stuff thats connected to M but lies lower than sea_z
    sea_grid = np.logical_or(dem.grid - sea_z <= 0, dem.grid == ND_VAL)
    mask = expand_water(sea_grid, mask, verbose=True)

    # Remove isolated blobs
    corr_mask = image.filters.correlate(mask.astype(np.uint8), np.ones((3, 3)))
    mask |= (corr_mask >= 8)
    dem.grid[mask] = sea_z

    return dem

def burn_lakes(dem, lake_grid, triangle_mask, tolerance):
    '''
    Burn lake into DEM.


    Arguments:
        dem:            thatsDEM.grid.Grid object with either a DTM or DSM.
        lake_mask:      Mask telling us where the lakes are.
        triangle_mask:  Mask showing where there are large triangles.
        tolerance:      Accepted difference between DEM values and lake-heights.

    Returns:
        dem with lakes burned into it.
    '''
    mask = (dem.grid - lake_grid) < tolerance
    #add large triangles
    mask |= triangle_mask
    #add no-data
    mask |= (dem.grid == ND_VAL)
    #remove small blobs
    corr_mask = image.filters.correlate(mask.astype(np.uint8), np.ones((3, 3)))
    mask |= (corr_mask >= 8)
    #restrict to lakes
    mask &= (lake_grid != ND_VAL)
    dem.grid[mask] = lake_grid[mask]

    return dem

# Each of these entries must be None OR of the form (cstr,sql) - sql is executed via OGR.
# This will fail if not castable to str.
NAMES = {"LAKE_LAYER": list,
         "LAKE_Z_LAYER": list,
         "LAKE_Z_ATTR": str,
         "RIVER_LAYER": list,
         "SEA_LAYER": list,
         "BUILD_LAYER": list}

def main(args):
    '''
    Main processing function
    '''

    pargs = parser.parse_args(args[1:])
    lasname = pargs.las_file
    kmname = constants.get_tilename(lasname)
    layer_def = pargs.layer_def
    fargs = dict.fromkeys(NAMES, None)
    if pargs.layer_def is not None:
        if layer_def.endswith(".json"):
            with open(layer_def) as layer_def_file:
                jargs = json.load(layer_def_file)
        else:
            jargs = json.loads(layer_def)
        fargs.update(jargs)

    for name in NAMES:
        res_type = NAMES[name]
        if fargs[name] is not None:
            try:
                fargs[name] = res_type(fargs[name])
            except TypeError as error_msg:
                print(str(error_msg))
                print(name + " must be convertable to %s" % repr(res_type))

    try:
        extent = np.asarray(constants.tilename_to_extent(kmname))
    except (ValueError, AttributeError) as error_msg:
        print("Exception: %s" % str(error_msg))
        print("Bad 1km formatting of las file: %s" % lasname)
        return 1

    extent_buf = extent + (-BUFBUF, -BUFBUF, BUFBUF, BUFBUF)
    cell_buf_extent = np.array([-CELL_BUF, -CELL_BUF, CELL_BUF, CELL_BUF], dtype=np.float64)
    grid_buf = (extent + cell_buf_extent * pargs.cell_size)
    buf_georef = [grid_buf[0], pargs.cell_size, 0, grid_buf[3], 0, -pargs.cell_size]

    #move these to a method in e.g. grid.py
    ncols = int(ceil((grid_buf[2] - grid_buf[0]) / pargs.cell_size))
    nrows = int(ceil((grid_buf[3] - grid_buf[1]) / pargs.cell_size))
    assert (extent_buf[:2] < grid_buf[:2]).all()
    assert modf((extent[2] - extent[0]) / pargs.cell_size)[0] == 0.0

    if not os.path.exists(pargs.output_dir):
        os.mkdir(pargs.output_dir)

    terrainname = os.path.join(pargs.output_dir, "dtm_" + kmname + ".tif")
    surfacename = os.path.join(pargs.output_dir, "dsm_" + kmname + ".tif")
    terrain_exists = os.path.exists(terrainname)
    surface_exists = os.path.exists(surfacename)
    if pargs.dsm:
        do_dsm = pargs.overwrite or (not surface_exists)
    else:
        do_dsm = False
    if do_dsm:
        do_dtm = True
    else:
        do_dtm = pargs.dtm and (pargs.overwrite or (not terrain_exists))
    if not (do_dtm or do_dsm):
        print("dtm already exists: %s" % terrain_exists)
        print("dsm already exists: %s" % surface_exists)
        print("Nothing to do - exiting...")
        return 2
    #### warn on smoothing #####
    if pargs.smooth_rad > CELL_BUF:
        print("Warning: smoothing radius is larger than grid buffer")

    tiles = get_neighbours(pargs.tile_cstr, kmname, pargs.rowcol_sql, pargs.tile_sql, pargs.remove_bridges_in_dtm)
    bufpc = None
    geoid = grid.fromGDAL(GEOID_GRID, upcast=True)
    for path, ground_cls, surf_cls, h_system in tiles:
        if os.path.exists(path):
            #check sanity
            assert set(ground_cls).issubset(set(surf_cls))
            assert h_system in ["dvr90", "E"]

            tile_pc = pointcloud.fromAny(path, include_return_number=True)
            tile_pc = tile_pc.cut_to_box(*extent_buf)
            tile_pc = tile_pc.cut_to_class(surf_cls)

            if tile_pc.get_size() > 0:
                mask = np.zeros((tile_pc.get_size(),), dtype=np.bool)
                #reclass hack
                for cls in ground_cls:
                    mask |= (tile_pc.c == cls)
                tile_pc.c[mask] = SYNTH_TERRAIN

                #warping to hsys
                if h_system != pargs.hsys and not pargs.nowarp:
                    if pargs.hsys == "E":
                        tile_pc.toE(geoid)
                    else:
                        tile_pc.toH(geoid)

                if bufpc is None:
                    bufpc = tile_pc
                else:
                    bufpc.extend(tile_pc)
            del tile_pc
        else:
            print("Neighbour " + path + " does not exist.")
    if bufpc is None:
        return 3

    if bufpc.get_size() <= 3:
        return 3

    rc1 = 0
    rc2 = 0
    dtm = None
    dsm = None
    triangle_mask = np.ndarray(0)

    water_mask, lake_raster, sea_mask, build_mask = setup_masks(fargs, nrows, ncols, buf_georef)

    # Remove terrain points in buildings
    if pargs.clean_buildings and (build_mask is not None) and build_mask.any():
        bmask_shrink = image.morphology.binary_erosion(build_mask)
        mask = bufpc.get_grid_mask(bmask_shrink, buf_georef)
        #validate thoroughly
        testpc1 = bufpc.cut(mask) # only building points(?)
        testpc2 = None
        try:
            testpc1.sort_spatially(2)
            mask &= (bufpc.c == SYNTH_TERRAIN)
            testpc2 = bufpc.cut(mask) # building points and terrain(?)
            in_building = ((testpc1.max_filter(2, xy=testpc2.xy, nd_val=ND_VAL) - testpc2.z) > 1)
            cut_buildings = np.zeros_like(mask, dtype=np.bool)
            if in_building.any():
                cut_buildings[mask] = in_building
            #so see if these are really, really inside buildings
            bufpc = bufpc.cut(np.logical_not(cut_buildings))
        except:
            pass
        finally:
            if testpc1 is not None:
                del testpc1
            if testpc2 is not None:
                del testpc2

    if do_dtm:
        terr_pc = bufpc.cut_to_class(SYNTH_TERRAIN)
        if terr_pc.get_size() > 3:
            dtm, trig_grid = gridit(terr_pc, grid_buf, pargs.cell_size, None, doround=pargs.round)
        else:
            rc1 = 3

        if dtm and not rc1:
            assert dtm.grid.shape == (nrows, ncols) #else something is horribly wrong...
            # Create a mask with triangles larger than triangle_limit.
            # Small triangles will be ignored and possibly filled out later.
            triangle_mask = trig_grid.grid > pargs.triangle_limit
        else:
            rc1 = 3

        if triangle_mask.any() and water_mask.any() and not rc1:
            if not pargs.no_expand_water:
                water_mask = expand_water(triangle_mask, water_mask)

            if build_mask is not None:
                water_mask &= np.logical_not(build_mask) #xor

            # Filling in large triangles
            mask = np.logical_and(triangle_mask, water_mask)
            zlow = array_geometry.tri_filter_low(
                terr_pc.z,
                terr_pc.triangulation.vertices,
                terr_pc.triangulation.ntrig,
                pargs.zlim)

            if pargs.debug:
                debug_difference = terr_pc.z - zlow
                print(debug_difference.mean(), (debug_difference != 0).sum())

            terr_pc.z = zlow
            dtm_low, trig_grid = gridit(terr_pc, grid_buf, pargs.cell_size, None, doround=pargs.round)
            dtm.grid[mask] = dtm_low.grid[mask]
            del dtm_low

            # Smooth water
            if pargs.flatten:
                flat_grid = array_geometry.masked_mean_filter(dtm.grid, mask, 4)
                dtm.grid[triangle_mask] = flat_grid[triangle_mask]

        #FIX THIS PART
        if pargs.smooth_rad > 0 and build_mask is not None and triangle_mask.any():
            # Smoothing below houses (probably)...
            mask = np.logical_and(triangle_mask, build_mask)
            dilated_mask = image.morphology.binary_dilation(mask)
            dilated_mask &= np.logical_not(water_mask)
            flat_grid = array_geometry.masked_mean_filter(dtm.grid, dilated_mask, pargs.smooth_rad)
            mask &= np.logical_not(water_mask)
            dtm.grid[mask] = flat_grid[mask]

            del flat_grid
            del trig_grid
            del dilated_mask
            del mask

        if pargs.burn_sea and (sea_mask is not None) and not rc1:
            dtm = burn_sea(dtm, sea_mask, triangle_mask, pargs.sea_z, pargs.sea_tolerance)

        # Burn lakes
        if lake_raster is not None and not rc1:
            burn_lakes(dtm, lake_raster, triangle_mask, pargs.lake_tolerance_dtm)

        if pargs.dtm and (pargs.overwrite or (not terrain_exists)):
            dtm.shrink(CELL_BUF).save(terrainname, dco=TIF_CREATION_OPTIONS, srs=SRS_WKT)

        del triangle_mask
        del terr_pc

    if do_dsm:
        surf_pc = bufpc.cut_to_return_number(1)
        del bufpc

        if surf_pc.get_size() > 3:
            dsm, trig_grid = gridit(surf_pc, grid_buf, pargs.cell_size, None, doround=pargs.round)
        else:
            rc2 = 3

        if dsm and not rc2:
            triangle_mask = trig_grid.grid > pargs.triangle_limit
        else:
            rc2 = 3

        #now we are in a position to handle water...
        if dtm and water_mask.any() and triangle_mask.any() and not rc2:
            # Fill large triangles
            mask = np.logical_and(triangle_mask, water_mask)
            dsm.grid[mask] = dtm.grid[mask]

            if pargs.debug:
                print(dsm.grid.shape)
                t_name = os.path.join(
                    pargs.output_dir, "triangles_" + kmname + ".tif")
                trig_grid.shrink(CELL_BUF).save(
                    t_name,
                    dco=["TILED=YES", "COMPRESS=LZW"])
                w_name = os.path.join(
                    pargs.output_dir, "water_" + kmname + ".tif")
                water_grid = grid.Grid(water_mask, dsm.geo_ref, 0)
                water_grid.shrink(CELL_BUF).save(w_name, dco=["TILED=YES", "COMPRESS=LZW"])

            if pargs.burn_sea and (sea_mask is not None):
                dsm = burn_sea(dsm, sea_mask, triangle_mask, pargs.sea_z, pargs.sea_tolerance)

            # Burn lakes
            if lake_raster is not None:
                burn_lakes(dsm, lake_raster, triangle_mask, pargs.lake_tolerance_dsm)

            del triangle_mask
        dsm.shrink(CELL_BUF).save(surfacename, dco=TIF_CREATION_OPTIONS, srs=SRS_WKT)

        del surf_pc

    return max(rc1, rc2)

if __name__ == "__main__":
    main(sys.argv)
