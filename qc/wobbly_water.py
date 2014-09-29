######################################################################################
## Test for water that aint flat (by using mean filter)
##
######################################################################################
import sys,os,time
#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry, report
from math import tan,radians
import numpy as np
import  thatsDEM.dhmqc_constants as constants
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)

cut_to=constants.water
zmin=0.2
frad=1.0 #filter radius
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Find steep triangles (in water class by default). Large triangles will be ignored...",prog=progname)
parser.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
#add some arguments below
parser.add_argument("-class",dest="cut_to",type=int,default=cut_to,help="Inspect points of this class - defaults to 'water'")
parser.add_argument("-zmin",type=float,default=zmin,help="Specify minimal z-distance to mean for a point that isn't flat. Defaults to %.2f m" %zmin)
parser.add_argument("-frad",type=float,default=frad,help="Specify the filtering radius in which to calculate mean. Defaults to %.2f m" %frad)
parser.add_argument("las_file",help="input las tile.")



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
	reporter=report.ReportWobbly(pargs.use_local)
	pc=pointcloud.fromLAS(lasname, cls=[pargs.cut_to])
	print("%d points of class %d in this tile..." %(pc.get_size(),pargs.cut_to))
	if pc.get_size()<3:
		print("Few points of class %d in this tile..." %pargs.cut_to)
		return 0
	print("Using z-limit %.2f deg" %pargs.zmin)
	pc.sort_spatially(pargs.frad)
	meanz=pc.mean_filter(pargs.frad)
	diff=pc.z-meanz
	M=(np.fabs(diff)>pargs.zmin)
	n=M.sum()
	print("Found %d wobbly points" %n)
	if n>0:
		pc=pc.cut(M)
		diff=diff[M]
		if n<1e5:
			for i in xrange(pc.xy.shape[0]):
				d=diff[i]
				pt=pc.xy[i]
				wkt="POINT(%.2f %.2f)"%(pt[0],pt[1])
				reporter.report(kmname,pargs.cut_to,d,wkt_geom=wkt)
		else:
			raise Exception("Too many points to report - use other filtering options!!")
		
	return 0
	
	
	
	
		

#to be able to call the script 'stand alone'
if __name__=="__main__":
	main(sys.argv)