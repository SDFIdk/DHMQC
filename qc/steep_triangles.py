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
######################################################################################
##  Test for water that aint flat... or just find steep triangles...
## pretty much like road_delta_check
######################################################################################
import sys,os,time
#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry
from db import report
from math import tan,radians
import numpy as np
import dhmqc_constants as constants
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)

cut_to=constants.water
xy_max=2 #dont care about triangles larger than this
zmin=0.05 #dont care about triangles smaller than this
min_slope=15 #default value for when something is sloping too much
dst_fieldname='DN'
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Find steep triangles (in water class by default). Large triangles will be ignored...",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
#add some arguments below
parser.add_argument("-class",dest="cut_to",type=int,default=cut_to,help="Inspect points of this class - defaults to 'water'")
parser.add_argument("-slope",type=float,default=min_slope,help="Specify the slope limit for when a triangle isn't flat. Defaults to %.2f deg" %min_slope)
parser.add_argument("-zmin",type=float,default=zmin,help="Specify minimal z-bounding box for a triangle which isn't flat. Defaults to %.2f m" %zmin)
parser.add_argument("las_file",help="input 1km las tile.")



#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
def usage():
	parser.print_help()
	

def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception,e:
		print(str(e))
		return 1
	lasname=pargs.las_file
	kmname=constants.get_tilename(lasname)
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportSteepTriangles(pargs.use_local)
	pc=pointcloud.fromAny(lasname, cls=[pargs.cut_to])
	
	print("%d points of class %d in this tile..." %(pc.get_size(),pargs.cut_to))
	if pc.get_size()<3:
		print("Few points of class %d in this tile..." %pargs.cut_to)
		return 0
	print("Using slope limit %.2f deg" %pargs.slope)
	pc.triangulate()
	tv2=tan(radians(pargs.slope))
	geom=pc.get_triangle_geometry()
	M=np.logical_and(geom[:,1]<xy_max,geom[:,2]>pargs.zmin)
	M&=(geom[:,0])>tv2
	geom=geom[M]  #save for reporting
	n=M.sum()
	print("Found %d steep triangles... reporting centers..." %n)
	if n==0:
		return 0
	centers=pc.triangulation.get_triangle_centers()[M] #only the centers of the interesting triangles
	slopes=np.degrees(np.arctan(np.sqrt(geom[:,0])))
	for i in xrange(centers.shape[0]):
		center=centers[i]
		slope=slopes[i]
		bbxy=geom[i][1]
		bbz=geom[i][2]
		wkt="POINT(%.2f %.2f)"%(center[0],center[1])
		reporter.report(kmname,pargs.cut_to,slope,bbxy,bbz,wkt_geom=wkt)
	return 0
	
	
	
	
		

#to be able to call the script 'stand alone'
if __name__=="__main__":
	main(sys.argv)