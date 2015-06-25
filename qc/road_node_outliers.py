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
#############################
## zcheck_abs script. Checks ogr point datasources against strips from pointcloud....
#############################
import sys,os,time
import math
import numpy as np
from osgeo import ogr
from thatsDEM import pointcloud,vector_io,array_geometry,array_factory,grid
from db import report
import dhmqc_constants as constants
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
#path to geoid 
GEOID_GRID=os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b_utm32.tif")
#The class(es) we want to look at...
CUT_CLASS=constants.terrain

#Default buffer size for cutlines (roads...)
BUF=30
#TODO: migrate to new argparse setup
progname=os.path.basename(__file__).replace(".pyc",".py")
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Check for outliers for each node in 3d line features",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
parser.add_argument("-class",dest="cut_to",type=int,default=CUT_CLASS,help="Specify ground class for input las file (will use default defined in constants).")
parser.add_argument("-id_attr",help="Specify id attribute to identify a line.")
parser.add_argument("-toH",action="store_true",help="Warp the pointcloud from ellipsoidal heights to dvr90.")
parser.add_argument("-zlim",type=float,default=1.0,help="Only report points that differ this much. Defaults to 1.0 m")
parser.add_argument("-srad",type=float,default=2.0,help="Use this search radius when interpolating (idw) in pointcloud. Defaults to 2.0 m")
parser.add_argument("-ndval",type=float,default=-999,help="Specify no-data value for line nodes (will be skipped). Defaults to -999")
parser.add_argument("-debug",action="store_true",help="Turn on extra verbosity...")
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database)")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("ref_data",help="Reference data (path, connection string etc).")

def usage():
    parser.print_help()




def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception,e:
        print(str(e))
        return 1
    kmname=constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
    lasname=pargs.las_file
    linename=pargs.ref_data
    use_local=pargs.use_local
    if pargs.schema is not None:
        report.set_schema(pargs.schema)
    reporter=report.ReportLineOutliers(use_local)
    try:
        extent=np.asarray(constants.tilename_to_extent(kmname))
    except Exception,e:
        print("Could not get extent from tilename.")
        raise e
    lines=vector_io.get_features(linename,pargs.layername,pargs.layersql,extent)
    print("Found %d features in %s" %(len(lines),linename))
    if len(lines)==0:
        return 2
    cut_input_to=pargs.cut_to
    print("Reading "+lasname+"....")
    pc=pointcloud.fromAny(lasname).cut_to_class(cut_input_to) #what to cut to here...??
    if pargs.debug:
        print("Cutting input pointcloud to class %d" %cut_input_to)
    if pc.get_size()<5:
        print("Few points in pointcloud!!")
        return 3
    if pargs.toH:
        geoid=grid.fromGDAL(GEOID_GRID,upcast=True)
        print("Using geoid from %s to warp to orthometric heights." %GEOID_GRID)
        pc.toH(geoid)
    print("Sorting...")
    pc.sort_spatially(pargs.srad)
    print("Starting loop..")
    n_found=0
    for line in lines:
        if pargs.id_attr is not None:
            line_id=line.GetFieldAsString(pargs.id_attr)
        else:
            line_id=""
        #explode
        geom=line.GetGeometryRef()
        ng=geom.GetGeometryCount()
        geoms_here=[geom]
        if ng>1:
            #so must be a multi-geometry - explode it
            geoms_here=[geom.GetGeometryRef(i).Clone() for i in range(ng)]
        for lg in geoms_here:
            xyz_ref=array_geometry.ogrline2array(lg,flatten=False)
            z_ref=xyz_ref[:,2].copy()
            xy_ref=xyz_ref[:,:2].copy()
            N=(z_ref!=pargs.ndval)
            if not N.all():
                print("Found nd-values... skipping those...")
                z_ref=z_ref[N]
                xy_ref=xy_ref[N]
            if xy_ref.shape[0]==0:
                return 2
            N=np.logical_and(xy_ref>=extent[:2],xy_ref<=extent[2:]).all(axis=1)
            xy_ref=xy_ref[N]
            z_ref=z_ref[N]
            if xy_ref.shape[0]==0:
                return 2
            if pargs.debug:
                print "all",xy_ref.shape[0]
            z_interp=pc.idw_filter(pargs.srad,xy=xy_ref,nd_val=-9999)
            dz=(z_interp-z_ref)
            M=np.logical_and(z_interp!=-9999,np.fabs(dz)>=pargs.zlim)
            if not M.any():
                continue
            z_ref=z_ref[M]
            xy_ref=xy_ref[M]
            dz=dz[M]
            if pargs.debug:
                print "bad",xy_ref.shape[0]
            #find the triangles
            for i in range(dz.shape[0]):
                wkt="POINT({0} {1} {2})".format(str(xy_ref[i,0]),str(xy_ref[i,1]),str(z_ref[i]))
                reporter.report(kmname,line_id,z_ref[i],dz[i],pargs.zlim,wkt_geom=wkt)
                n_found+=1
    print("Reported %d pts. with large deviation." %n_found)
    return 0	
            


if __name__=="__main__":
    main(sys.argv)
    