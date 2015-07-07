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
parser=ArgumentParser(description="Check accuracy relative to GCPs - we assume here that GCPs are very sparse, otherwise use the z_accuracy script.",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
parser.add_argument("-class",dest="cut_to",type=int,default=CUT_CLASS,help="Specify ground class for input las file (will use default defined in constants).")

parser.add_argument("-toE",action="store_true",help="Warp the points from dvr90 to ellipsoidal heights.")
parser.add_argument("-z",help="z attribute of reference point layer (defaults to 'Z')",default="Z")
parser.add_argument("-debug",action="store_true",help="Turn on extra verbosity...")
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database)",type=str)
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
	pointname=pargs.ref_data
	use_local=pargs.use_local
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportZcheckAbsGCP(use_local)
	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception,e:
		print("Could not get extent from tilename.")
		extent=None
	xy_ref=[]
	z_ref=[]
	feats=vector_io.get_features(pointname,pargs.layername,pargs.layersql,extent)
	print("Found %d features in %s" %(len(feats),pointname))
	if len(feats)==0:
		return 2
	for f in feats:
		x,y=f.GetGeometryRef().GetPoint_2D()
		z=f[pargs.z]
		xy_ref.append((x,y))
		z_ref.append(z)
	xy_ref=np.asarray(xy_ref,dtype=np.float64)
	z_ref=np.asarray(z_ref,dtype=np.float64)
	cut_input_to=pargs.cut_to
	print("Reading "+lasname+"....")
	pc=pointcloud.fromAny(lasname).cut_to_class(cut_input_to) #what to cut to here...??
	if pargs.debug:
		print("Cutting input pointcloud to class %d" %cut_input_to)
	if pc.get_size()<5:
		print("Few points in pointcloud!!")
		return 3
	#warping here....
	if (pargs.toE):
		geoid=grid.fromGDAL(GEOID_GRID,upcast=True)
		print("Using geoid from %s to warp to ellipsoidal heights." %GEOID_GRID)
		toE=geoid.interpolate(xy_ref)
		assert((toE!=geoid.nd_val).all())
		z_ref+=toE
	#pc.triangulate()
	#trig_geom=pc.get_triangle_geometry()
	#I=pc.find_triangles(xy_ref)
	#M=(I>=0)
	#if not M.all():
	#	print("Warning, %d points fall outside triangulation." %(np.logical_not(M).sum()))
	#	xy_ref=xy_ref[M]
	#	z_ref=z_ref[M]
	#	I=I[M]
	#trig_geom=trig_geom[I]
	#z_interp=pc.interpolate(xy_ref,nd_val=-9999)
	#dz=z_interp-z_ref
	for i in range(xy_ref.shape[0]):
		xy=xy_ref[i].reshape(1,2).copy()
		xy1=xy-(BUF,BUF)
		xy2=xy+(BUF,BUF)
		pc_=pc.cut_to_box(xy1[0,0],xy1[0,1],xy2[0,0],xy2[0,1])
		if pargs.debug:
			print xy, xy.shape
			print("Points in buffer: %d" %pc_.get_size())
		wkt="POINT({0} {1} {2})".format(str(xy[0,0]),str(xy[0,1]),str(z_ref[i]))
		
		if pc_.get_size()<3:
			print("Too few points in pointcloud around GCP: "+wkt)
			continue
		pc_.triangulate()
		trig_geom=pc_.get_triangle_geometry()
		I=pc_.find_triangles(xy)
		j=I[0]
		if j<0:
			print("Point "+wkt+" falls outside (local) triangulation...")
			continue
		trig_geom=trig_geom[j]
		z_interp=pc_.interpolate(xy,nd_val=-9999)
		dz=z_interp-z_ref[i]
		angle=math.degrees(math.atan(math.sqrt(trig_geom[0])))
		xy_box=trig_geom[1]
		reporter.report(kmname,z_ref[i],dz,angle,xy_box,wkt_geom=wkt)
	return 0	
			


if __name__=="__main__":
	main(sys.argv)