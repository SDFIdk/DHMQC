###########################
## beginnings of building zcheck...
#########################
import sys,os
import numpy as np
import zcheck_base
from thatsDEM import report
DEBUG="-debug" in sys.argv

unclassified=1
xy_tolerance=1.0
z_tolerance=1.0
angle_tolerance=60


def main(args):
	lasname=args[1]
	buildname=args[2]
	use_local="-use_local" in args
	done=zcheck_base.zcheck_base(lasname,buildname,angle_tolerance,xy_tolerance,z_tolerance,unclassified,
	report_layer_name=report.Z_CHECK_BUILD_TABLE,use_local=use_local,DEBUG=DEBUG)
				

if __name__=="__main__":
	main(sys.argv)
				
				
				
				
		
	
	