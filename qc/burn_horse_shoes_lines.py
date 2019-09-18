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

from __future__ import absolute_import
from __future__ import print_function
import sys,os,time
import math
#import some relevant modules...
from .thatsDEM import pointcloud, vector_io, array_geometry, grid, triangle
from .db import report
import shutil
import numpy as np
from osgeo import gdal, ogr
from . import dhmqc_constants as constants
from .utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)

#####################################################################################
##  Burn horse shoes by generating 3d lines. Would be better to generate and store the lines and then just use gdal_rasterize.
#####################################################################################


progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Burn horse shoes by generating 3d lines. Would be better to generate and store the lines and then just use gdal_rasterize.",prog=progname)
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database). "+vector_io.EXTENT_WKT +
" can be used as a placeholder for wkt-geometry of area of interest - in order to enable a significant speed up of db queries",type=str)
parser.add_argument("dem_tile",help="input 1km dem tile.")
parser.add_argument("horse_ds",help="input connection string for horse shoe database")
parser.add_argument("dem_all",help="Seamless dem covering all tiles (vrt or similar)")
parser.add_argument("outdir",help="Output directory for resulting DEM files")
parser.add_argument("-debug",help="TODO")



#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
def usage():
    parser.print_help()






def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception as e:
        print((str(e)))
        return 1
    kmname=constants.get_tilename(pargs.dem_tile)
    print(("Running %s on block: %s, %s" %(progname,kmname,time.asctime())))
    extent=np.asarray(constants.tilename_to_extent(kmname))
    shoes=vector_io.get_geometries(pargs.horse_ds,pargs.layername,pargs.layersql,extent)
    outname=os.path.join(pargs.outdir,"dhym_lines_"+kmname+".tif")
    if len(shoes)==0:
        print("No shoes, man!")
        shutil.copy(pargs.dem_tile,outname)
        return 0
    #We allways interpolate values from the large ds (vrt) which is not changed in the loop below.
    dtm=grid.fromGDAL(pargs.dem_tile)
    cs=dtm.geo_ref[1]
    mesh_xy=pointcloud.mesh_as_points(dtm.shape,dtm.geo_ref)
    dem_ds=gdal.Open(pargs.dem_all)
    dem_band=dem_ds.GetRasterBand(1)
    ndval=dem_band.GetNoDataValue()
    georef=np.asarray(dem_ds.GetGeoTransform())
    m_drv=ogr.GetDriverByName("Memory")
    line_ds = m_drv.CreateDataSource( "dummy")
    layer = line_ds.CreateLayer( "lines", None, ogr.wkbLineString25D)
    layerdefn=layer.GetLayerDefn()
    #if True:
    #  import matplotlib
    #  matplotlib.use("Qt4Agg")
    #   mport matplotlib.pyplot as plt
    for shoe in shoes:
        arr=array_geometry.ogrline2array(shoe,flatten=True)
        assert(arr.shape[0]==4)
        #okie dokie - now load a small raster around the horseshoe
        #the shoes can have quite long 'sides', however the two 'ends' should be small enough to keep in memory - so load two grids along the two 'ends'
        small_grids=[]
        for e in ((0,3),(1,2)):
            xy=arr[e,:] #take the corresponding edge
            ll=xy.min(axis=0)
            ur=xy.max(axis=0)
            #map to pixel-space
            ll_pix=grid.user2array(georef,ll)
            ur_pix=grid.user2array(georef,ur)
            xwin,mywin=(ur_pix-ll_pix) #negative ywin
            #Buffer grid slightly - can do with less I suppose...
            xoff=max(0,int(ll_pix[0])-2)
            yoff=max(0,int(ur_pix[1])-2)
            xwin=min(int(xwin+1),dem_ds.RasterXSize-xoff-4)+4
            ywin=min(int(1-mywin),dem_ds.RasterYSize-yoff-4)+4
            #If not completely contained in large raster - continue??
            assert(xoff>=0 and yoff>=0 and xwin>=1 and ywin>=1) #hmmm
            piece=dem_band.ReadAsArray(xoff,yoff,xwin,ywin).astype(np.float64)
            #What to do with nodata-values??
            N=(piece==ndval)
            if N.any():
                print("WARNING: setting nodata values to 0!!!")
                piece[N]=0
            piece_georef=georef.copy()
            piece_georef[0]+=xoff*georef[1]
            piece_georef[3]+=yoff*georef[5]
            small_grids.append(grid.Grid(piece,piece_georef,ndval))
        dxy1=arr[3]-arr[0] # 0 to 3
        dxy2=arr[2]-arr[1] # 1 to 2
        ndxy1=np.sqrt(np.dot(dxy1,dxy1.T))
        ndxy2=np.sqrt(np.dot(dxy2,dxy2.T))
        nsteps=int(max(math.ceil(max(ndxy1,ndxy2)/cs),2))
        h=np.linspace(0,1,nsteps,endpoint=True).reshape((nsteps,1))
        l1=h*dxy1+arr[0]
        l2=h*dxy2+arr[1]
        z1=small_grids[0].interpolate(l1)
        z2=small_grids[1].interpolate(l2)
        assert((z1!=ndval).all())
        assert((z2!=ndval).all())
        for i in range(nsteps):
            line=ogr.Geometry(ogr.wkbLineString25D)
            line.AddPoint(l1[i,0],l1[i,1],z1[i])
            line.AddPoint(l2[i,0],l2[i,1],z2[i])
            feature=ogr.Feature(layerdefn)
            feature.SetGeometry(line)
            res=layer.CreateFeature(feature)
    #ok - layer created, Burn it!!
    layer.ResetReading()
    arr=vector_io.just_burn_layer(layer,dtm.geo_ref,dtm.shape,nd_val=ndval,dtype=np.float32,all_touched=True,burn3d=True)
    M=(arr!=ndval)
    #arr[M]-=255 #What! seems to be a byte off???
    # print arr[M].max(),arr[M].min()
    assert M.any()
    #drv=ogr.GetDriverByName("SQLITE")
    #drv.CopyDataSource(line_ds,os.path.join(pargs.outdir,"shoes2.sqlite"))
    layer=None
    line_ds=None
    dtm.grid[M]=arr[M]
    dtm.save(outname)
    return 0








#to be able to call the script 'stand alone'
if __name__=="__main__":
    main(sys.argv)
