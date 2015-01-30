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
import sys,os,time
import  thatsDEM.dhmqc_constants as constants
from argparse import ArgumentParser
import math
import glob
import numpy as np
from subprocess import call
from thatsDEM import pointcloud
from osgeo import osr


#Call from qc_warp with this command line: "python qc_wrap.py dem_gen d:\temp\slet\raa\*.las -targs "D://temp//slet//output" "

#gridsize of the hillshade (always 0.4 m)
gridsize = 0.4

cut_terrain=[2,9,17]
zlim=1.5
EPSG_CODE=25832 #default srs
SRS=osr.SpatialReference()
SRS.ImportFromEPSG(EPSG_CODE)
SRS_WKT=SRS.ExportToWkt()
SRS_PROJ4=SRS.ExportToProj4()
ND_VAL=-9999

progname=os.path.basename(__file__)
parser=ArgumentParser(description="Generate DTM for a las file. Will try to read surrounding tiles for buffer.",prog=progname)
parser.add_argument("las_file",help="Input las tile.")
parser.add_argument("output_dir",help="Where to store the hillshade e.g. c:\\final_resting_place\\")

def usage():
	parser.print_help()
		
def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	lasfolder = os.path.dirname(lasname)
	kmname=constants.get_tilename(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	print("Size limit is : %d" %pargs.size_lim)
	print("Using default srs: %s" %(SRS_PROJ4))
	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	
	
	
	basisname,extname=os.path.splitext(os.path.basename(lasname))
	terrainname=os.path.join(pargs.output_dir,"dtm_"+kmname+".tif")
	
	if os.path.exists(terrainname) and not pargs.overwrite:
		print(terrainname+" already exists... exiting...")
		return 1
	pc=pointcloud.fromLAS(lasname)
	pc.triangulate()
	
	A=pc.triangulation.make_grid_low(2500,2500,extent[0],gridszie,extent[3],gridsize,nd_val=ND_VAL,cut_off=zlim)
	g.grid=g.grid.astype(np.float32)
	if (g.grid==ND_VAL).all():
		return 3
	
	g.save(terrainname, dco=["TILED=YES","COMPRESS=DEFLATE","PREDICTOR=3","ZLEVEL=9"],srs=SRS_WKT)
	#delete grid from memory to save RAM...
	del g
	return 0
	
	
	

	
	
if __name__=="__main__":
	main(sys.argv)
	
