###########################
## beginnings of building zcheck...
#########################
import sys,os
import numpy as np
import zcheck_base
import dhmqc_constants as const
from thatsDEM import report
DEBUG="-debug" in sys.argv

cut_to=[const.surface,const.building]
xy_tolerance=1.0
z_tolerance=1.0
angle_tolerance=60


def main(args):
	lasname=args[1]
	buildname=args[2]
	use_local="-use_local" in args
	reporter=report.ReportZcheckBuilding(use_local)
	done=zcheck_base.zcheck_base(lasname,buildname,angle_tolerance,xy_tolerance,z_tolerance,cut_to,reporter)
				

if __name__=="__main__":
	main(sys.argv)
				
				
				
				
		
	
	