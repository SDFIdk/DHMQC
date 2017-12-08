# Copyright (c) 2015-2016, Danish Geodata Agency <gst@gst.dk>
# Copyright (c) 2016, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
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
## beginnings of building zcheck...
#########################
import sys,os
import numpy as np
import zcheck_base
import dhmqc_constants as const
from db import report
from utils.osutils import ArgumentParser
DEBUG="-debug" in sys.argv

cut_to=[const.building,const.surface] 
xy_tolerance=1.0
z_tolerance=1.0
angle_tolerance=60

progname=os.path.basename(__file__).replace(".pyc",".py")
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Check strip overlap on buildings.",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
parser.add_argument("-class",dest="cut_to",type=int,default=cut_to,help="Inspect points of this class - defaults to 'building' and 'surface'")
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database)",type=str)
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("build_data",help="input building reference data (path or connection string).")

def usage():
	parser.print_help()

def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	buildname=pargs.build_data
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportZcheckBuilding(pargs.use_local)
	done=zcheck_base.zcheck_base(lasname,buildname,angle_tolerance,xy_tolerance,z_tolerance,pargs.cut_to,reporter,layername=pargs.layername,layersql=pargs.layersql)
				

if __name__=="__main__":
	main(sys.argv)
				
				
				
				
		
	

