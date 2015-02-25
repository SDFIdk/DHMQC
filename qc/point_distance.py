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
import os,sys
import time
import subprocess
import numpy as np
from osgeo import osr
from thatsDEM import dhmqc_constants as constants
from thatsDEM import pointcloud,grid
from utils.osutils import ArgumentParser  
import math
SRS=osr.SpatialReference()
SRS.ImportFromEPSG(constants.EPSG_CODE)
SRS_WKT=SRS.ExportToWkt()
CUT_TO=[constants.terrain,constants.water,constants.bridge]
CELL_SIZE=1.0  #100 m cellsize in density grid
TILE_SIZE=constants.tile_size   #1000  yep - its 1km tiles...
GRIDS_OUT="distance_grids"  #due to the fact that this is being called from qc_wrap it is easiest to have a standard folder for output...
SRAD=4.0

progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Calculate point distance",prog=progname)
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("-cs",type=float,help="Specify cell size of grid, defaults to "+str(CELL_SIZE),default=CELL_SIZE)
parser.add_argument("-nocut",action="store_true",help="Do NOT cut to default terrain grid classes.")
parser.add_argument("-srad",type=float,help="Search radius for points. Defaults to "+str(SRAD),default=SRAD)
parser.add_argument("-outdir",help="Specify output directory. Defaults to "+GRIDS_OUT,default=GRIDS_OUT)


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
	try:
		extent=constants.tilename_to_extent(kmname)
	except Exception,e:
		print("Bad tilename:")
		print(str(e))
		return 1
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	cs=pargs.cs
	ncols_f=TILE_SIZE/cs
	ncols=int(ncols_f)
	nrows=ncols  #tiles are square (for now)
	if ncols!=ncols_f:
		print("TILE_SIZE: %d must be divisible by cell size..." %(TILE_SIZE))
		usage()
		return 1
	georef=[extent[0],cs,0,extent[3],0,-cs]
	print("Using cell size: %.2f" %cs)
	outdir=pargs.outdir
	if not os.path.exists(outdir):
		os.mkdir(outdir)
	outname_base="dist_{0:.0f}_".format(cs)+os.path.splitext(os.path.basename(lasname))[0]+".tif"
	outname=os.path.join(outdir,outname_base)
	print("Reading %s, writing %s" %(lasname,outname))
	pc=pointcloud.fromLAS(lasname)
	if not pargs.nocut:
		pc=pc.cut_to_class(CUT_TO)
	print("Sorting...")
	pc.sort_spatially(pargs.srad)
	print("Filtering...")
	xy=pointcloud.mesh_as_points((nrows,ncols),georef)
	d=pc.distance_filter(pargs.srad,xy=xy,nd_val=9999).reshape((nrows,ncols))
	g=grid.Grid(d,georef,9999)
	g.save(outname,dco=["TILED=YES","COMPRESS=LZW"],srs=SRS_WKT)
	return 0
	

if __name__=="__main__":
	main(sys.argv)