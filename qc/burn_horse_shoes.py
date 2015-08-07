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

import sys,os,time
import math
#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry, grid, triangle
from db import report
import numpy as np
from osgeo import gdal
import dhmqc_constants as constants
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
RESOLUTION=1.0 #spacing between lines
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Write something here",prog=progname)
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database). "+vector_io.EXTENT_WKT +
" can be used as a placeholder for wkt-geometry of area of interest - in order to enable a significant speed up of db queries",type=str)
parser.add_argument("dem_tile",help="input 1km dem tile.")
parser.add_argument("horse_ds",help="input connection string for horse shoe database")
parser.add_argument("dem_all",help="Seamless dem covering all tiles (vrt or similar)")
parser.add_argument("outdir",help="Output directory for resulting DEM files")
parser.add_argument("-debug",help="Show triangulations!")



#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
def usage():
    parser.print_help()
    

TARGET=np.array((0,0,0,1,1,1,1,0),dtype=np.float64)

def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception,e:
        print(str(e))
        return 1
    kmname=constants.get_tilename(pargs.dem_tile)
    print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
    extent=np.asarray(constants.tilename_to_extent(kmname))
    shoes=vector_io.get_geometries(pargs.horse_ds,pargs.layername,pargs.layersql,extent)
    if len(shoes)==0:
        return 0
    dtm=grid.fromGDAL(pargs.dem_tile)
    mesh_xy=pointcloud.mesh_as_points(dtm.shape,dtm.geo_ref)
    dem_ds=gdal.Open(pargs.dem_all)
    dem_band=dem_ds.GetRasterBand(1)
    ndval=dem_band.GetNoDataValue()
    georef=np.asarray(dem_ds.GetGeoTransform())
    #if True:
    #  import matplotlib
    #    matplotlib.use("Qt4Agg")
    #  import matplotlib.pyplot as plt
    for shoe in shoes:
        arr=array_geometry.ogrline2array(shoe,flatten=True)
        assert(arr.shape[0]==4)
        #okie dokie - now load a small raster around the horseshoe 
        ll=arr.min(axis=0)
        ur=arr.max(axis=0)
        cm=arr.mean(axis=0)
        #map to pixel-space
        ll_pix=grid.user2array(georef,ll)
        ur_pix=grid.user2array(georef,ur)
        xwin,mywin=(ur_pix-ll_pix) #negative ywin
        xoff=max(0,int(ll_pix[0])-1)
        yoff=max(0,int(ur_pix[1])-1)
        xwin=min(int(xwin+1),dem_ds.RasterXSize-xoff-1)+1
        ywin=min(int(1-mywin),dem_ds.RasterYSize-yoff-1)+1
        print xoff,yoff,xwin,ywin
        #If not completely contained in large raster - continue??
        assert(xoff>=0 and yoff>=0 and xwin>=1 and ywin>=1) #hmmm
        piece=dem_band.ReadAsArray(xoff,yoff,xwin,ywin).astype(np.float64)
        piece_georef=georef[:]
        piece_georef[0]+=xoff*georef[1]
        piece_georef[3]+=yoff*georef[5]
        small_grid=grid.Grid(piece,piece_georef,ndval)
        print "grid", small_grid.get_bounds()
        print "shoe", ll,ur
        #Now construct two refined lines 
        dxy1=arr[2]-arr[1] # 1 to 2
        dxy2=arr[3]-arr[0] # 0 to 3
        print "dx",dxy1,dxy2
        ndxy1=np.sqrt(np.dot(dxy1,dxy1.T))
        ndxy2=np.sqrt(np.dot(dxy2,dxy2.T))
        print ndxy1,ndxy2
        nsteps=max(math.ceil(max(ndxy1,ndxy2)/RESOLUTION),2)
        l1=np.linspace(0,ndxy1,nsteps,endpoint=True).reshape((nsteps,1))*dxy1/ndxy1+arr[1]
        l2=np.linspace(0,ndxy2,nsteps,endpoint=True).reshape((nsteps,1))*dxy2/ndxy2+arr[0]
        z1=small_grid.interpolate(l1)
        z2=small_grid.interpolate(l2)
        N=np.arange(0,nsteps)
        with open(os.path.join(pargs.outdir,"l1.csv"),"w") as f:
            f.write("x,y,z,n\n")
            np.savetxt(f,np.column_stack((l1,z1,N)),delimiter=",")
        with open(os.path.join(pargs.outdir,"l2.csv"),"w") as f:
            f.write("x,y,z,n\n")
            np.savetxt(f,np.column_stack((l2,z2,N)),delimiter=",")
        
        #now move to cm-coords
        scale=(ndxy1+ndxy2)*0.5
        tarr=(arr-cm)/scale
        #setup equations
        A=np.zeros((8,8),dtype=np.float64)
        A[::2,0]=tarr[:,0]
        A[::2,1]=tarr[:,1]
        A[::2,2]=1
        A[1:,3:6]=A[:-1,:3]
        A[:,6]=A[:,0]+A[:,3]
        A[:,7]=A[:,1]+A[:,4]
        A[:,6]*=-TARGET
        A[:,7]*=-TARGET
        if abs(np.linalg.det(A))<1e-3:
            raise Exception("Small determinant!")
        h=np.linalg.solve(A,TARGET)
        H=np.append(h,(1,)).reshape((3,3))
        T=np.column_stack((tarr,np.ones((4,))))
        v=np.dot(H,T.T)
        b=v[-1,:].copy()
        v=v/b
        res=(v.T)[:,:-1]
        print res
        miss=np.fabs(res-TARGET.reshape((4,2))).max()
        print("Numerical miss: %.15g" %miss)
        assert(miss<0.1)
        #now construct a psudo-grid
        Z=np.column_stack((z2,z1))
        cs=float(1)/(nsteps-1)
        pseudo_georef=[-0.5,1.0,0,1+0.5*cs,0,-cs]
        pseudo_grid=grid.Grid(Z,pseudo_georef,ndval)
        print "HEY",pseudo_grid.get_bounds()
        #transform input points!
        mxy=(mesh_xy-cm)/scale
        mxy=np.column_stack((mxy,np.ones((mxy.shape[0],)))) #append projective last coord
        mxy=np.dot(H,mxy.T)
        p=mxy[-1,:].copy()
        mxy=mxy/p
        mxy=(mxy.T)[:,:-1]
        M=np.logical_and(mxy[:,0]<=1,mxy[:,0]>=0)
        M&=mxy[:,1]>=0
        M&=mxy[:,1]<=1
        mxy_in_grid=mxy[M]
        print("Centers in horseshoe: %d" % mxy_in_grid.shape[0])
        new_z=pseudo_grid.interpolate(mxy_in_grid)
        print new_z.max(),new_z.min(),new_z.mean()
        print z1.max(),z1.min(),z2.max(),z2.min(), z1.mean(),z2.mean()
        print mxy_in_grid.min(axis=0)
        print mxy_in_grid.max(axis=0)
        M=M.reshape(dtm.shape)
        dtm.grid[M]=new_z
        #N1=np.arange(0,nsteps-1)
        #N2=N1+1
        #N3=N1+nsteps
        #N4=N3+1
        #T1=np.column_stack((N1,N3,N4))
        #T2=np.column_stack((N4,N2,N1))
        #T=np.vstack((T1,T2))
        #plt.figure()
        #plt.triplot(xy[:,0],xy[:,1],T)
        #plt.plot(arr[:,0],arr[:,1],color="green")
        #plt.plot(l1[:,0],l1[:,1],".",color="blue",ms=10)
        #plt.plot(l2[:,0],l2[:,1],".",color="red",ms=10)
        #plt.show()
        outname=os.path.join(pargs.outdir,"dhym_"+kmname+".tif")
        dtm.save(outname)
        
        
    
        
            
        
        
    
    
#to be able to call the script 'stand alone'
if __name__=="__main__":
    main(sys.argv)