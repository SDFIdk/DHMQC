###########################
## beginnings of road zcheck...
## Almost exact copy of zcheck_byg - merge??
#########################
import sys,os
import numpy as np
from thatsDEM import report
import thatsDEM.dhmqc_constants as const
import zcheck_base
DEBUG="-debug" in sys.argv

#SOME GLOBALS WHICH SHOULD BE PLACED IN A CONSTANTS MODULE


xy_tolerance=1.5
z_tolerance=0.25
angle_tolerance=25
buffer_dist=2.0

cut_to=const.terrain


def main(args):
	lasname=args[1]
	roadname=args[2]
	use_local="-use_local" in args
	reporter=report.ReportZcheckRoad(use_local)
	done=zcheck_base.zcheck_base(lasname,roadname,angle_tolerance,xy_tolerance,z_tolerance,cut_to,reporter,buffer_dist=buffer_dist)
	

if __name__=="__main__":
	main(sys.argv)
				
				
				
				
		
	
	