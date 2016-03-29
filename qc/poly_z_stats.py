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
import sys,os,time
#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry, grid
from db import report
import numpy as np
import dhmqc_constants as constants
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
z_min=1.0
cut_to=constants.building
#Path to geoid grid
GEOID_GRID=os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b_utm32.tif")
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Report height statistics for a specific class in polygons",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
#add some arguments below
parser.add_argument("-class",type=int,default=cut_to,dest="ccut",help="Inspect points of this class - defaults to 'building'")
parser.add_argument("-nowarp",action="store_true",help="Pointcloud is already in dvr90 - so do not warp. Default is to assume input is in ellipsoidal heights.")
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database). "+vector_io.EXTENT_WKT +
" can be used as a placeholder for wkt-geometry of area of interest - in order to enable a significant speed up of db queries",type=str)
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("poly_ds",help="input reference data connection string (e.g to a db, or just a path to a shapefile).")


#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
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
    extent=np.asarray(constants.tilename_to_extent(kmname))
    reporter=report.ReportZStatsInPolygon(pargs.use_local)
    polys=vector_io.get_geometries(pargs.poly_ds,pargs.layername,pargs.layersql,extent)
    print("Number of polygons: %d" %len(polys))
    if len(polys)==0:
        return 3
    pc=pointcloud.fromAny(pargs.las_file).cut_to_class(pargs.ccut)
    print("Number of points of class %s: %d" %(str(pargs.ccut),pc.size))
    if not pargs.nowarp:
        #Warp to dvr90 if needed (default)
        geoid=grid.fromGDAL(GEOID_GRID,upcast=True)
        pc.toH(geoid)
        del geoid
    for poly in polys:
        arr=array_geometry.ogrpoly2array(poly,flatten=True)
        pc_in_poly=pc.cut_to_polygon(arr)
        n=pc_in_poly.size
        if pc_in_poly.size>0:
            z1=pc_in_poly.z.min()
            z2=pc_in_poly.z.max()
            zm=pc_in_poly.z.mean()
            sd=np.std(pc_in_poly.z)
            f5=np.percentile(pc_in_poly.z,5)
        else:
            z1=0
            z2=0
            zm=0
            sd=0
            f5=0
        reporter.report(kmname,pargs.ccut,n,z1,z2,zm,sd,f5,ogr_geom=poly)
    

#to be able to call the script 'stand alone'
if __name__=="__main__":
    main(sys.argv)
