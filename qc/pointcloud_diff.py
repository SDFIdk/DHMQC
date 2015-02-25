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
import numpy as np
from osgeo import ogr
from thatsDEM import pointcloud,vector_io,array_geometry,report,array_factory,grid
import thatsDEM.dhmqc_constants as constants
from utils.osutils import ArgumentParser

#path to geoid 
GEOID_GRID=os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b.utm32")
#The class(es) we want to look at...
CUT_CLASS=constants.terrain
#The z-interval we want to consider for the input LAS-pointcloud...
Z_MIN=constants.z_min_terrain
Z_MAX=constants.z_max_terrain
CELL_SIZE=10  #10 m cellsize in diff grid
TILE_SIZE=constants.tile_size
ND_VAL=-9999
MIN_POINT_LIMIT=2  #at least this number of reference points in order to grid...
MIN_POINT_LIMIT_BASE=5 # at least this many point in input las to bother
GRIDS_OUT="diff_grids"  #due to the fact that this is being called from qc_wrap it is easiest to have a standard folder for output..
SRAD=2.0

progname=os.path.basename(__file__).replace(".pyc",".py")

parser=ArgumentParser(description="'Subtracts' two pointclouds and grids the difference.",prog=progname)
#add some arguments below
parser.add_argument("-class",dest="cut_to",type=int,default=CUT_CLASS,help="Specify ground class of reference las tile. Defaults to 'terrain'")
parser.add_argument("-outdir",help="Specify an output directory. Default is "+GRIDS_OUT+" in cwd.",default=GRIDS_OUT)
parser.add_argument("-cs",type=float,help="Specify cell size of grid. Default 100 m (TILE_SIZE must be divisible by cs)",default=CELL_SIZE)
parser.add_argument("-toE",action="store_true",help="Warp reference points to ellipsoidal heights.")
parser.add_argument("-srad",type=float,help="Specify search radius to get interpolated z in input. Defaults to "+str(SRAD),default=SRAD)
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("las_ref_file",help="reference las tile.")

def usage():
	parser.print_help()
	


def check_points(dz):
	m=dz.mean()
	sd=np.std(dz)
	n=dz.size
	print("+"*60)
	print("DZ-stats (input/new - reference . Outliers NOT removed):")
	print("Mean:               %.2f m" %m)
	print("Standard deviation: %.2f m" %sd)
	print("N-points:           %d" %n)
	


			
		
	
	


def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception,e:
		print(str(e))
		return 1
	#standard dhmqc idioms....#
	lasname=pargs.las_file
	pointname=pargs.las_ref_file
	kmname=constants.get_tilename(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	try:
		xul,yll,xur,yul=constants.tilename_to_extent(kmname)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	outdir=pargs.outdir
	if not os.path.exists(outdir):
		os.mkdir(outdir)
	cut_to=pargs.cut_to
	cs=pargs.cs
	ncols_f=TILE_SIZE/cs
	ncols=int(ncols_f)
	nrows=ncols  #tiles are square (for now)
	if ncols!=ncols_f:
		print("TILE_SIZE: %d must be divisible by cell size...(cs=%.2f)\n" %(TILE_SIZE,cs))
		return 1
	print("Using cell size: %.2f" %cs)
	pc=pointcloud.fromLAS(lasname).cut_to_z_interval(Z_MIN,Z_MAX).cut_to_class(CUT_CLASS) #what to cut to here...??
	if pc.get_size()<MIN_POINT_LIMIT_BASE:
		print("Few points, %d, in input pointcloud , won't bother..." %pc.get_size())
		return 0
	pc_ref=pointcloud.fromLAS(pointname).cut_to_class(cut_to)
	print("%d points in reference pointcloud." %pc_ref.get_size())
	if pc_ref.get_size()<MIN_POINT_LIMIT:
		print("Too few, %d, reference points - sorry..." %pc_ref.get_size())
		return 0
	if pargs.toE:
		geoid=grid.fromGDAL(GEOID_GRID,upcast=True)
		print("Using geoid from %s to warp to ellipsoidal heights." %GEOID_GRID)
		toE=geoid.interpolate(pc_ref.xy)
		M=(toE==geoid.nd_val)
		if M.any():
			raise Warning("Warping to ellipsoidal heights produced no-data values!")
			toE=toE[M]
			pc_ref=pc_ref.cut(M)
		pc_ref.z+=toE
	t0=time.clock()
	pc.sort_spatially(pargs.srad)
	z_new=pc.idw_filter(pargs.srad,xy=pc_ref.xy,nd_val=ND_VAL)
	M=(z_new!=ND_VAL)
	z_new=z_new[M]
	pc_ref=pc_ref.cut(M)
	geo_ref=[xul,cs,0,yul,0,-cs]
	dz=z_new-pc_ref.z
	check_points(dz)
	pc_ref.z=dz
	pc_ref.sort_spatially(0.7*cs)
	xy=pointcloud.mesh_as_points((nrows,ncols),geo_ref)
	
	t1=time.clock()
	dz_grid=pc_ref.mean_filter(0.6*cs,xy=xy,nd_val=ND_VAL).reshape((nrows,ncols)) #or median here...
	t2=time.clock()
	print("Final filtering: %.3f s" %(t2-t1))
	print("All in all: %.3f s" %(t2-t0))
	g=grid.Grid(dz_grid,geo_ref,ND_VAL)
	outname_base="diff_{0:.0f}_".format(cs)+os.path.splitext(os.path.basename(lasname))[0]+".tif"
	outname=os.path.join(outdir,outname_base)
	g.save(outname,dco=["TILED=YES","COMPRESS=LZW"])
	
	return 0
	
if __name__=="__main__":
	main(sys.argv)
			
			
	
	