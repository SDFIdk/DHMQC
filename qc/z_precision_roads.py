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
###########################
## road zcheck... Check delta for overlaps along roads
#########################
import sys,os
import numpy as np
from db import report
import dhmqc_constants as const
import zcheck_base
from utils.osutils import ArgumentParser

#SOME GLOBALS WHICH SHOULD BE PLACED IN A CONSTANTS MODULE


xy_tolerance=1.5
z_tolerance=0.25
angle_tolerance=25
buffer_dist=2.0

cut_to=const.terrain

progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Check strip overlaps along roads.",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
#add some arguments below
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database)")
parser.add_argument("-class",dest="cut_to",type=int,default=cut_to,help="Inspect points of this class - defaults to 'terrain'")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("road_data",help="input road reference data.")


def usage():
	parser.print_help()

def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	roadname=pargs.road_data
	cut=pargs.cut_to
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportZcheckRoad(pargs.use_local)
	done=zcheck_base.zcheck_base(lasname,roadname,angle_tolerance,xy_tolerance,z_tolerance,cut,reporter,buffer_dist=buffer_dist,layername=pargs.layername,layersql=pargs.layersql)
	

if __name__=="__main__":
	main(sys.argv)
				
				
				
				
		
	
	