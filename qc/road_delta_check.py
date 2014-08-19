######################################################################################
## Delta check: check for steepnes along roads to find terrain classification failures.
## work in progress...
######################################################################################
import sys,os,time
from thatsDEM import pointcloud, vector_io, array_geometry, report
from utils.names import get_1km_name
import numpy as np
import  thatsDEM.dhmqc_constants as constants
import argparse

cut_to=constants.terrain #default to terrain only...
line_buffer=1.5 #
#LIMITS FOR STEEP TRIANGLES... will also imply limits for angles...
xy_max=1.5  #flag triangles larger than this as invalid
z_min=0.4


#Argument handling
parser=argparse.ArgumentParser(description="Check for steepnes along road center lines.")
parser.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
parser.add_argument("-class",dest="cut_class",type=int,default=cut_to,help="Inspect points of this class - defaults to 'terrain'")
parser.add_argument("-zlim",dest="zlim",type=float,default=z_min,help="Specify the minial z-size of a steep triangle.")
parser.add_argument("-runid",dest="runid",help="Set run id for the database...")
parser.add_argument("-schema",dest="schema",help="Set database schema")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("lines",help="input reference road lines.")

def usage():
	parser.print_help()
	sys.exit()
			

def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	linename=pargs.lines
	kmname=get_1km_name(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	reporter=report.ReportDeltaRoads(pargs.use_local)
	cut_class=pargs.cut_class
	pc=pointcloud.fromLAS(lasname).cut_to_class(cut_class)
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
	lines=vector_io.get_geometries(linename)
	nf=0
	for line in lines:
		xy=array_geometry.ogrline2array(line,flatten=True)
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
	