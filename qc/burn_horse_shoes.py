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

#######################################################################
#
# Demo of horseshoe burning.
#
#######################################################################
#
# Hydrological horseshoes are irregular quadrilaterals indicating
# areas where natural or man made occlusions have rendered a terrain
# model hydrologically meaningless, e.g. by introducing holes in dykes
# or blockings in rivers.
#
# The horseshoe ABCD consists of an open end AD, a closed end BC and
# two extruders AB and CD.
#
# When registering the horseshoe, the operator must ensure that the
# open end and the closed end represent hydrologically meaningful
# profiles in the terrain model.
#
# Repairing the DTM consists of the following steps:
#
#     1   Select N, the number of points in each profile
#         (AD, resp. BC).
#         N = max(|AD|, |BC|)/d + 1, where d is the ground
#         sample distance of the DTM grid.
#
#    2    Generate the two hydrologically meaningful profiles
#         by bilinear interpolation in the DTM grid.
#         For the next steps of the repair procedure it will be
#         beneficial to represent the two profiles as a N-by-2
#         "profile grid", P.
#
#    3    For each DTM grid node inside the horseshoe, assign a
#         new height value by bilinear interpolation in P.
#
# This sample implementation simplifies the interpolation by introducing
# a projective mapping of the horseshoe onto the unit square [0,1]*[0,1].
#
#######################################################################



from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import time
import math

import numpy as np
import shutil

#import some relevant modules...
from .thatsDEM import pointcloud, vector_io, array_geometry, grid, triangle
from .db       import report
from osgeo    import gdal

from . import dhmqc_constants as constants

# If you want this script to be included in the test-suite use this subclass.
# Otherwise argparse.ArgumentParser will be the best choice :-)
from .utils.osutils import ArgumentParser

# To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")

RESOLUTION=1.0 #spacing between lines

# Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
# a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser =  ArgumentParser(description="Apply hydrological modifications ('horse shoes') to DTM.",prog=progname)
group  =  parser.add_mutually_exclusive_group()
group.add_argument("-layername",  help = "Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",   help = "Specify sql-statement for layer selection (e.g. for reference data in a database). "+vector_io.EXTENT_WKT +
" can be used as a placeholder for wkt-geometry of area of interest - in order to enable a significant speed up of db queries",type=str)

parser.add_argument("dem_tile",  help = "1km dem tile to be generated.")
parser.add_argument("horse_ds",  help = "input connection string for horse shoe database")
parser.add_argument("dem_all",   help = "Seamless dem covering all tiles (vrt or similar)")
parser.add_argument("outdir",    help = "Output directory for resulting DEM files")
parser.add_argument("-debug",    help = "Show triangulations!")



# A usage function will be imported by wrapper to print usage for test
# otherwise ArgumentParser will handle that...
def usage():
    parser.print_help()


TARGET=np.array((0, 0, 1, 0, 1, 1, 0, 1),  dtype = np.float64)


def transform(xy, cm, scale, H):
    xy = (xy - cm)/scale
    xy = np.column_stack((xy, np.ones((xy.shape[0],)))) #append projective last coord
    xy = np.dot(H, xy.T)
    p  = xy[-1,:].copy()
    xy = xy / p
    xy = (xy.T)[:,:-1]
    return xy


def inverse_transform(xy, cm, scale, Hinv):
    xy = np.column_stack((xy, np.ones((xy.shape[0],)))) #append projective last coord
    xy = np.dot(Hinv, xy.T)
    p  = xy[-1,:].copy()
    xy = xy / p
    xy = (xy.T)[:,:-1]
    xy = xy * scale + cm
    return xy


def get_transformation_params(arr):
    cm = arr.mean(axis = 0)
    dxy1  = arr[2]-arr[1] # 1 to 2
    dxy2  = arr[3]-arr[0] # 0 to 3
    ndxy1 = np.sqrt(np.dot(dxy1,dxy1.T))
    ndxy2 = np.sqrt(np.dot(dxy2,dxy2.T))

    #now move to cm-coords
    nsteps = max(math.ceil(max(ndxy1,ndxy2)/RESOLUTION),2)
    scale  = (ndxy1 + ndxy2)*0.5
    tarr   = (arr - cm)/scale

    #setup equations
    A=np.zeros((8,8),  dtype = np.float64)
    A[::2,0]   =  tarr[:,0]
    A[::2,1]   =  tarr[:,1]
    A[::2,2]   =  1
    A[1:,3:6]  =  A[:-1,:3]

    A[:,6]  = A[:,0]+A[:,3]
    A[:,7]  = A[:,1]+A[:,4]
    A[:,6] *= -TARGET
    A[:,7] *= -TARGET

    if abs(np.linalg.det(A)) < 1e-3:
        raise Exception("Small determinant!")
    h = np.linalg.solve(A,TARGET)
    H = np.append(h,(1,)).reshape((3,3))

    # check numerical miss here
    res  = transform(arr,cm,scale,H)
    miss = np.fabs(res-TARGET.reshape((4,2))).max()
    print(("Numerical miss: %.15g" %miss))
    assert(miss < 0.1)
    return cm,  scale,  nsteps,  H,np.linalg.inv(H)


def main(args):
    try:
        pargs = parser.parse_args(args[1:])
    except Exception as e:
        print((str(e)))
        return 1

    kmname = constants.get_tilename(pargs.dem_tile)
    print(("Running %s on block: %s, %s" %(progname,kmname,time.asctime())))
    extent = np.asarray(constants.tilename_to_extent(kmname))

    shoes  = vector_io.get_geometries(pargs.horse_ds,  pargs.layername,  pargs.layersql,extent)
    outname = os.path.join(pargs.outdir,  "dhym_" + kmname + ".tif")
    if len(shoes) == 0:
        print("No shoes, man!")
        shutil.copy(pargs.dem_tile,outname)
        return 0
    # We always interpolate values from the large dataset (vrt) which is not changed in the loop below.
    dtm = grid.fromGDAL(pargs.dem_tile)
    mesh_xy  =  pointcloud.mesh_as_points(dtm.shape,  dtm.geo_ref)
    dem_ds   =  gdal.Open(pargs.dem_all)
    dem_band =  dem_ds.GetRasterBand(1)
    ndval    =  dem_band.GetNoDataValue()
    georef   =  np.asarray(dem_ds.GetGeoTransform())

    #if True:
    #  import matplotlib
    #  matplotlib.use("Qt4Agg")
    #  import matplotlib.pyplot as plt

    for shoe in shoes:
        arr = array_geometry.ogrline2array(shoe,  flatten = True)
        assert(arr.shape[0]==4)

        # okie dokie - now load a small raster around the horseshoe
        # the shoes can have quite long 'sides' (extruders),
        # however the two 'ends' should be small enough to keep in
        # memory - so load two grids along the two 'ends'
        cm, scale, nsteps, H, Hinv = get_transformation_params(arr)
        small_grids = []
        for e in ((0,3),(1,2)):
            xy = arr[e,:] # take the corresponding edge
            ll = xy.min(axis = 0)
            ur = xy.max(axis = 0)

            # map to pixel-space
            ll_pix = grid.user2array(georef, ll)
            ur_pix = grid.user2array(georef, ur)
            xwin, mywin = (ur_pix - ll_pix) #negative ywin

            # Buffer grid slightly - can do with less I suppose...
            xoff = max(0, int(ll_pix[0])-2)
            yoff = max(0, int(ur_pix[1])-2)
            xwin = min(int(xwin+1),  dem_ds. RasterXSize - xoff - 4) + 4
            ywin = min(int(1-mywin), dem_ds. RasterYSize - yoff - 4) + 4
            # If not completely contained in large raster - continue??
            assert(xoff>=0 and yoff>=0 and xwin>=1 and ywin>=1) #hmmm
            piece = dem_band.ReadAsArray(xoff, yoff, xwin, ywin).astype(np.float64)

            # What to do with nodata-values??
            N = (piece==ndval)
            if N.any():
                print("WARNING: setting nodata values to 0!!!")
                piece[N]=0

            piece_georef = georef.copy()
            piece_georef[0] += xoff*georef[1]
            piece_georef[3] += yoff*georef[5]
            small_grids.append(grid.Grid(piece, piece_georef, ndval))

        # Make sure that the grid is 'fine' enough - since the projective transformation
        # will distort distances across the lines we want to subdivide
        cs = 1 / float(nsteps)

        # check numerical diff
        moved  = np.array(((0,cs),(1,cs),(1,1-cs),(0,1-cs)))
        tmoved = inverse_transform(moved,cm,scale,Hinv)
        delta  = arr-tmoved
        ndelta = np.sqrt(np.sum(delta**2,axis=1))
        nrows  = int(nsteps*ndelta.max())+1

        # construct the  vertical two lines, along the two 'ends', in projective space
        hspace, cs = np.linspace(1,  0,  nrows,endpoint = True,  retstep = True)
        cs = -cs
        l1 = np.zeros((nrows,2),dtype=np.float64)
        l1[:,1] = hspace
        l2 = np.ones((nrows,2), dtype = np.float64)
        l2[:,1] = hspace
        tl1 =  inverse_transform(l1, cm, scale, Hinv)
        tl2 =  inverse_transform(l2, cm, scale, Hinv)
        z1  =  small_grids[0].interpolate(tl1)
        z2  =  small_grids[1].interpolate(tl2)
        assert((z1 != ndval).all())
        assert((z2 != ndval).all())

        # now construct a psudo-grid in 'projective space'
        Z = np.column_stack((z1,z2))
        pseudo_georef = [-0.5, 1.0, 0, 1 + 0.5*cs, 0, -cs]
        pseudo_grid = grid.Grid(Z,pseudo_georef, ndval)

        # Transform input points!
        # first cut to bounding box of shoe
        M = np.logical_and(mesh_xy >= arr.min(axis = 0),  mesh_xy <= arr.max(axis = 0)).all(axis = 1)
        print(("Number of points in bb: %d" %M.sum()))

        xy_small = mesh_xy[M]
        txy = transform(xy_small, cm, scale, H)
        N = np.logical_and(txy >= 0,  txy <= 1).all(axis = 1)
        xy_in_grid = txy[N]
        print(("Number of points in shoe: %d" %xy_in_grid.shape[0]))
        new_z = pseudo_grid.interpolate(xy_in_grid)

        # Construct new mask as N is 'relative' to M
        MM = np.zeros((mesh_xy.shape[0]),  dtype = np.bool)
        MM[M] = N
        MM = MM.reshape(dtm.shape)
        dtm.grid[MM] = new_z

        # OLD STUFF FOR TRIANGULATION APPROACH
        # N1 = np.arange(0,nsteps-1)
        # N2 = N1 + 1
        # N3 = N1+nsteps
        # N4 = N3+1
        # T1 = np.column_stack((N1,N3,N4))
        # T2 = np.column_stack((N4,N2,N1))
        # T  = np.vstack((T1,T2))
        #
        # plt.figure()
        # plt.triplot(xy[:,0], xy[:,1], T)
        # plt.plot(arr[:,0], arr[:,1],    color = "green")
        # plt.plot(l1[:,0], l1[:,1], ".", color = "blue", ms = 10)
        # plt.plot(l2[:,0], l2[:,1], ".", color = "red",  ms = 10)
        # plt.show()
    dtm.save(outname,dco = ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3", "ZLEVEL=9"])









#to be able to call the script 'stand alone'
if __name__=="__main__":
    main(sys.argv)
