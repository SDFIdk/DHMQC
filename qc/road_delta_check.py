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
## Delta check: check for steepnes along roads to find terrain classification failures.
## work in progress...
######################################################################################
import sys,os,time
from thatsDEM import pointcloud, vector_io, array_geometry
from db import report
import numpy as np
import dhmqc_constants as constants
from utils.osutils import ArgumentParser

cut_to=constants.terrain #default to terrain only...
line_buffer=1.0 #
#LIMITS FOR STEEP TRIANGLES... will also imply limits for angles...
xy_max=1.5  #flag triangles larger than this as invalid
z_min=0.4

progname=os.path.basename(__file__)

#Argument handling - this is the pattern to be followed in order to check arguments from a wrapper...
parser=ArgumentParser(description="Check for steepnes along road center lines.",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
parser.add_argument("-class",dest="cut_class",type=int,default=cut_to,help="Inspect points of this class - defaults to 'terrain'")
parser.add_argument("-zlim",dest="zlim",type=float,default=z_min,help="Specify the minial z-size of a steep triangle.")
parser.add_argument("-runid",dest="runid",help="Set run id for the database...")
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database)")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("lines",help="input reference road lines.")



def usage():
	parser.print_help()
	

def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	linename=pargs.lines
	kmname=constants.get_tilename(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportDeltaRoads(pargs.use_local)
	cut_class=pargs.cut_class
	pc=pointcloud.fromLAS(lasname).cut_to_class(cut_class)
	if pc.get_size()<5:
		print("Too few points to bother..")
		return 1
	pc.triangulate()
	#tanv2,xy_size,z_size
	geom=pc.get_triangle_geometry()
	print("Using z-steepnes limit {0:.2f} m".format(pargs.zlim))
	M=np.logical_and(geom[:,1]<xy_max,geom[:,2]>pargs.zlim)
	geom=geom[M]  #save for reporting
	if not M.any():
		print("No steep triangles found...")
		return 0
	centers=pc.triangulation.get_triangle_centers()[M] #only the centers of the interesting triangles
	print("{0:d} steep triangles in tile.".format(centers.shape[0]))
	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception,e:
		print("Could not get extent from tilename.")
		extent=None
	lines=vector_io.get_geometries(linename,pargs.layername,pargs.layersql,extent)
	nf=0
	for line in lines:
		xy=array_geometry.ogrline2array(line,flatten=True)
		if xy.shape[0]==0:
			print("Seemingly an unsupported geometry...")
			continue
		#select the triangle centers which lie within line_buffer of the road segment
		M=array_geometry.points_in_buffer(centers,xy,line_buffer)
		critical=centers[M]
		print("*"*50)
		print("{0:d} steep centers along line {1:d}".format(critical.shape[0],nf))
		nf+=1
		if critical.shape[0]>0:
			z_box=geom[M][:,2]
			z1=z_box.max()
			z2=z_box.min()
			wkt="MULTIPOINT("
			for pt in critical:
				
				wkt+="{0:.2f} {1:.2f},".format(pt[0],pt[1])
			wkt=wkt[:-1]+")"
			reporter.report(kmname,z1,z2,wkt_geom=wkt)
	
		
		
if __name__=="__main__":
	main(sys.argv)
	