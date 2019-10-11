# -*- coding: utf-8 -*-

'''
flow_to_byte.py

Make a recalculation of dhm/flow from floating point to byte.

'''

import os
import sys
import subprocess
import argparse
from . import dhmqc_constants as constants

# Can be called from a project file containing following statements: 
# TESTNAME="flow_to_byte"
# INPUT_TILE_CONNECTION=r"onetiletif.sqlite"
# TARGS=["c:/output"]
# print (TARGS)



parser = argparse.ArgumentParser(description="Script simplifying flow rasters (float to byte translation)")
parser.add_argument("flowin", help="path to the 1km-tile to be treated containing floating point data")
parser.add_argument("flowoutdir", help="path to output simplified files (one byte per cell)")


def usage():
    '''
    Print usage
    '''
    parser.print_help()


def main(args):
    '''
    Main function
    '''
    try:
        pargs = parser.parse_args(args[1:])
    except TypeError as error_msg:
        print(str(error_msg))
        return 1

    flow_in = (pargs.flowin)
	
    kmname = constants.get_tilename(pargs.flowin)
    kmname = 'flowbyte_'+kmname+'.tif'
	
    flow_out = os.path.join(pargs.flowoutdir,kmname)
    exestr = 'gdal_calc --calc="1*((A>=1) * (A<10)) + 2*((A>=10) * (A <25)) + 3*((A>=25) * (A <50)) +4*((A>=50) * (A <100)) + 5*((A>=100)* (A <1000)) + 6*((A>=1000)* (A <10000))+ 7*((A>=10000)* (A <100000))+ 8*((A>=100000)* (A <1000000))+ 9*((A>=1000000)* (A <10000000)) + 10*((A>=10000000)* (A <100000000))+ 11*((A>=100000000)* (A <1000000000))+ 12*((A>=1000000000))" -A %s --outfile %s --type Byte  --NoDataValue=0 --co="COMPRESS=DEFLATE" --quiet' %(flow_in, flow_out)
    subprocess.call(exestr, shell=True)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
