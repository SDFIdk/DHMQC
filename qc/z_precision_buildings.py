###########################
## beginnings of building zcheck...
#########################
import sys,os
import numpy as np
import zcheck_base
import thatsDEM.dhmqc_constants as const
from thatsDEM import report
from utils.osutils import ArgumentParser
DEBUG="-debug" in sys.argv

cut_to=[const.building,const.surface] 
xy_tolerance=1.0
z_tolerance=1.0
angle_tolerance=60

progname=os.path.basename(__file__).replace(".pyc",".py")
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Check strip overlap on buildings.",prog=progname)
parser.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
parser.add_argument("-class",dest="cut_to",type=int,default=cut_to,help="Inspect points of this class - defaults to 'building' and 'surface'")
#add some arguments below
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("ref_file",help="input building reference data.")

def usage():
	parser.print_help()

def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	buildname=pargs.ref_file
	reporter=report.ReportZcheckBuilding(pargs.use_local)
	done=zcheck_base.zcheck_base(lasname,buildname,angle_tolerance,xy_tolerance,z_tolerance,pargs.cut_to,reporter)
				

if __name__=="__main__":
	main(sys.argv)
				
				
				
				
		
	
	