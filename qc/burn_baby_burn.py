# Copyright (c) 2015, Danish Geodata Agency <gst@gst.dk>
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



import sys
import os
import time
import math

import numpy as np
import shutil


from osgeo    import gdal
from osgeo    import ogr
from osgeo    import osr

#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry, grid, triangle
from db       import report


import dhmqc_constants as constants

# If you want this script to be included in the test-suite use this subclass.
# Otherwise argparse.ArgumentParser will be the best choice :-)
from utils.osutils import ArgumentParser

# To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")

#RESOLUTION=1.0 #spacing between lines

# Argument handling - if module has a parser attribute it will be used to check arguments in wrapper script.
# a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser =  ArgumentParser(description="Apply hydrological modifications ('horse shoes', 3d lines) to DTM.",prog=progname)
parser.add_argument("-horsesql",   help = "sql to select relevant horseshoes",type=str)
parser.add_argument("-linesql_own_z",help="sql to select 3d lines where the features z coordinate will be burnt.",type=str)
parser.add_argument("-linesql_dtm_z",help="sql to select lines where the values to be burn will be fetched from the DTM in the lines endpoints.",type=str)
parser.add_argument("-burn_as_lines",action="store_true",help="burn by generating a lot of 3d lines! Else use projective transformations.") 
parser.add_argument("dem_tile",  help = "1km dem tile to be generated.")
parser.add_argument("vector_ds",  help = "input connection string for database containing layers to be burnt.")
parser.add_argument("dem_all",   help = "Seamless dem covering all tiles (vrt or similar)")
parser.add_argument("outdir",    help = "Output directory for resulting DEM files")
parser.add_argument("-debug", action="store_true",   help = "Do something!")



# A usage function will be imported by wrapper to print usage for test
# otherwise ArgumentParser will handle that...
def usage():
    parser.print_help()

#The target 1 by on 1 square for the projective map
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


def get_transformation_params(arr,resolution):
    cm = arr.mean(axis = 0)
    dxy1  = arr[2]-arr[1] # 1 to 2
    dxy2  = arr[3]-arr[0] # 0 to 3
    ndxy1 = np.sqrt(np.dot(dxy1,dxy1.T))
    ndxy2 = np.sqrt(np.dot(dxy2,dxy2.T))

    #now move to cm-coords
    nsteps = max(math.ceil(max(ndxy1,ndxy2)/resolution),2)
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
    print("Numerical miss: %.15g" %miss)
    assert(miss < 0.1)
    return cm,  scale,  nsteps,  H,np.linalg.inv(H)


class ConstantGrid(object):
    """
    Duck typing the grid.Grid class.
    This is just a class with an interpolate method which returns constant values.
    """
    def __init__(self,val):
        self.val=float(val)
    def interpolate(self,xy):
        z=np.ones((xy.shape[0],),dtype=np.float64)*self.val
        return z

def get_dtm_piece(xy, dem_band, georef, ndval):
    """Load a small piece of a DEM (with georef=georef and no data value ndval)"""
   
    ll = xy.min(axis = 0)
    ur = xy.max(axis = 0)
    # map to pixel-space
    ll_pix = grid.user2array(georef, ll)
    ur_pix = grid.user2array(georef, ur)
    xwin, mywin = (ur_pix - ll_pix) #negative ywin

    # Buffer grid slightly - can do with less I suppose...
    xoff = max(0, int(ll_pix[0])-2)
    yoff = max(0, int(ur_pix[1])-2)
    xwin = min(int(xwin+1),  dem_band.XSize - xoff - 4) + 4
    ywin = min(int(1-mywin),  dem_band.YSize - yoff - 4) + 4
    
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
    
    return grid.Grid(piece, piece_georef, ndval)

def create_3d_lines(stuff_to_handle,layer,resolution,ndval):
    """Create a bunch of 3d lines needed to burn horseshoes"""
    layerdefn=layer.GetLayerDefn()
    for arr,g1,g2 in stuff_to_handle:
        assert(arr.shape[0]==4)
        dxy1=arr[3]-arr[0] # 0 to 3
        dxy2=arr[2]-arr[1] # 1 to 2
        ndxy1=np.sqrt(np.dot(dxy1,dxy1.T))
        ndxy2=np.sqrt(np.dot(dxy2,dxy2.T))
        nsteps=int(max(math.ceil(max(ndxy1,ndxy2)/resolution),2))
        h=np.linspace(0,1,nsteps,endpoint=True).reshape((nsteps,1))
        l1=h*dxy1+arr[0]
        l2=h*dxy2+arr[1]
        z1=g1.interpolate(l1)
        z2=g2.interpolate(l2)
        assert((z1!=ndval).all())
        assert((z2!=ndval).all())
        for i in range(nsteps):
            line=ogr.Geometry(ogr.wkbLineString25D)
            line.AddPoint(l1[i,0],l1[i,1],z1[i])
            line.AddPoint(l2[i,0],l2[i,1],z2[i])
            feature=ogr.Feature(layerdefn)
            feature.SetGeometry(line)
            res=layer.CreateFeature(feature)
            assert(res==0)
    
def burn_projective(stuff_to_handle,dtm,resolution,ndval,mesh_xy):
    """modify the dtm in place"""
    for arr,g1,g2 in stuff_to_handle:
        assert(arr.shape[0]==4)

        # okie dokie - now load a small raster around the horseshoe
        # the shoes can have quite long 'sides' (extruders),
        # however the two 'ends' should be small enough to keep in
        # memory - so load two grids along the two 'ends'
        cm, scale, nsteps, H, Hinv = get_transformation_params(arr,resolution)
       
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
        z1  =  g1.interpolate(tl1)
        z2  =  g2.interpolate(tl2)
        assert((z1 != ndval).all())
        assert((z2 != ndval).all())

        # now construct a psudo-grid in 'projective space'
        Z = np.column_stack((z1,z2))
        pseudo_georef = [-0.5, 1.0, 0, 1 + 0.5*cs, 0, -cs]
        pseudo_grid = grid.Grid(Z,pseudo_georef, ndval)

        # Transform input points!
        # first cut to bounding box of shoe
        M = np.logical_and(mesh_xy >= arr.min(axis = 0),  mesh_xy <= arr.max(axis = 0)).all(axis = 1)
        print("Number of points in bb: %d" %M.sum())

        xy_small = mesh_xy[M]
        txy = transform(xy_small, cm, scale, H)
        N = np.logical_and(txy >= 0,  txy <= 1).all(axis = 1)
        xy_in_grid = txy[N]
        print("Number of points in shoe: %d" %xy_in_grid.shape[0])
        new_z = pseudo_grid.interpolate(xy_in_grid)

        # Construct new mask as N is 'relative' to M
        MM = np.zeros((mesh_xy.shape[0]),  dtype = np.bool)
        MM[M] = N
        MM = MM.reshape(dtm.shape)
        dtm.grid[MM] = new_z
        

def main(args):
    try:
        pargs = parser.parse_args(args[1:])
    except Exception as e:
        print(str(e))
        return 1

    kmname = constants.get_tilename(pargs.dem_tile)
    print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
    extent = np.asarray(constants.tilename_to_extent(kmname))

    
    outname = os.path.join(pargs.outdir,  "dhym_" + kmname + ".tif")
   
       
    # We always interpolate values from the large dataset (vrt) which is not changed in the loop below.
    dtm = grid.fromGDAL(pargs.dem_tile)
    dem_ds   =  gdal.Open(pargs.dem_all)
    dem_band =  dem_ds.GetRasterBand(1)
    ndval    =  dem_band.GetNoDataValue()
    georef   =  np.asarray(dem_ds.GetGeoTransform())
    cell_res = min(georef[1], -georef[5] ) #the minimal cell size 
    
    #get the geometries!
    # a list of (geometry_as_np_array, 'grid1', 'grid2') - the grids should be objects with an interpolate method. The first represents the line 0-3, while the other one represents 1-2.
    # and yes, keep all that in memory. Buy some more memory if you need it, man!
    stuff_to_handle=[]
    #get relevant geometries and process 'em
    if pargs.horsesql is not None:
        #fetch the horseshoes
        shoes  = vector_io.get_geometries(pargs.vector_ds, layersql =  pargs.horsesql, extent= extent )
        #for the horse shoes we want to read z from the dtm!
        for shoe in shoes:
            arr = array_geometry.ogrline2array(shoe,  flatten = True)
            assert(arr.shape[0]==4)
            g1=get_dtm_piece(arr[(0,3),:],dem_band, georef, ndval) #the 'small' piece for the line from p0 to p3.
            g2=get_dtm_piece(arr[(1,2),:],dem_band, georef, ndval) #the 'small' piece for the line from p0 to p3.
            stuff_to_handle.append((arr,g1,g2))
        del shoes
    for sql,own_z in ((pargs.linesql_own_z,True),(pargs.linesql_dtm_z,False)):
        #handle the two line types in one go...
        if sql is not None:
            #fetch the 3d lines
            lines= vector_io.get_geometries(pargs.vector_ds, layersql =  sql , extent= extent)
            print("%d features in "%len(lines)+sql)
            for line in lines:
                arr = array_geometry.ogrline2array(line,  flatten = not own_z) 
                if own_z:
                    assert (arr.shape[1]==3) #should be a 3d geometry!!!
                    z=arr[:,2]
                #construct a horse shoe pr line segment!
                #should we assert that there are exactly two points?
                #We can handle the general case, but it gets tricky to determine what the interpolation should mean (z1 and z2 from endpoints of linestring and interpolating via relative length?)
                xy=arr[:,:2]
                n= xy.shape[0] - 1 # number of segments.
                #SO: for now assert that n==1, only one segment. Else modify what the grids should be for the 'inner' vertices...
                assert(n==1)
                #vectorice - even though there should be only one segment. Will handle the general case...
                N=array_geometry.linestring_displacements(xy)*(cell_res) #displacement vectors - probably too broad with all touched!!!!
                buf_left=xy+N
                buf_right=xy-N
                for i in range(n): # be prepared to handle the general case!!!
                    shoe=np.vstack((buf_left[i],buf_left[i+1],buf_right[i+1],buf_right[i])) # a horseshoe which is open in the 'first end'
                    if own_z:
                        g1=ConstantGrid(z[i])
                        g2=ConstantGrid(z[i+1])
                    else:
                        g1=get_dtm_piece(shoe[(0,3),:],dem_band, georef, ndval) #the 'small' piece for the line from p0 to p3.
                        g2=get_dtm_piece(shoe[(1,2),:],dem_band, georef, ndval) #the 'small' piece for the line from p0 to p3.
                    stuff_to_handle.append((shoe,g1,g2))
            del lines
    if len(stuff_to_handle)==0:
        print("No features to burn, copying dtm...")
        shutil.copy(pargs.dem_tile,outname)
        dem_band=None
        dem_ds=None
        return 0
    t1=time.time()
    if pargs.burn_as_lines:
        print("Burning as lines...")
        m_drv=ogr.GetDriverByName("Memory")
        line_ds = m_drv.CreateDataSource( "dummy")
        layer = line_ds.CreateLayer( "lines", osr.SpatialReference(dtm.srs), ogr.wkbLineString25D)
        create_3d_lines(stuff_to_handle,layer,cell_res*0.6,ndval) #will add 3d lines to layer (in place) - increase resolution to cell_res*0.8 for fewer lines
        print("Number of lines: %d" %layer.GetFeatureCount())
        #ok - layer created, Burn it!!
        layer.ResetReading()
        arr=vector_io.just_burn_layer(layer,dtm.geo_ref,dtm.shape,nd_val=ndval,dtype=np.float32,all_touched=True,burn3d=True)
        M=(arr!=ndval)
        assert M.any()
        if pargs.debug:
            drv=ogr.GetDriverByName("SQLITE")
            drv.CopyDataSource(line_ds,os.path.join(pargs.outdir,"dalines_"+kmname+".sqlite"))
        layer=None
        line_ds=None
        dtm.grid[M]=arr[M]
    else:
        mesh_xy  =  pointcloud.mesh_as_points(dtm.shape,  dtm.geo_ref)
        print("Burning using projective transformation...")
        burn_projective(stuff_to_handle,dtm,cell_res,ndval,mesh_xy)
    t2=time.time()
    print("Burning took: %.3fs" %(t2-t1))
    dtm.save(outname,dco = ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3", "ZLEVEL=9"])









#to be able to call the script 'stand alone'
if __name__=="__main__":
    main(sys.argv)
