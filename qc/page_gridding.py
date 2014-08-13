import os,sys
import time
import subprocess
import numpy as np
from osgeo import gdal,ogr
import thatsDEM.dhmqc_constants as constants
from utils.names import get_1km_name
import math
PAGE=os.path.join(os.path.dirname(__file__),"lib","page")
PAGE_SURFACE_ARGS=[PAGE,"-SR:1"]
for c in [constants.terrain,constants.low_veg,constants.med_veg,constants.high_veg,constants.building,constants.water,constants.bridge]:
	PAGE_SURFACE_ARGS.append("-SC:{0:d}".format(c))
PAGE_TERRAIN_ARGS=[PAGE,"-SC:{0:d}".format(constants.terrain),"-SC:{0:d}".format(constants.water)]
PAGE_PREDICTOR_SWITCH="-p"
PAGE_PREDICTOR_FRMT="id:{0:.2f}/2" #square power...
PAGE_GRID_FRMT="G/{0:.2f}/{1:.2f}/{2:.0f}/{3:.0f}/{4:.4f}/-9999"
CELL_SIZE=1.0  #100 m cellsize in density grid
TILE_SIZE=1000  #yep - its 1km tiles...
GRIDS_OUT="grids"
#input arguments as a list.... Popen will know what to do with it....
def run_command(args):
	prc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
	stdout,stderr=prc.communicate()
	return prc.poll(),stdout,stderr

def usage():
	print("Simple wrapper of 'page' with IDW predictor.")
	print("To run:")
	print("%s <las_tile> (options)" %(os.path.basename(sys.argv[0])))
	print("Options:")
	print("-cs <cell_size> to specify cell size of grid. Default 1 m (TILE_SIZE must be divisible by cs)")
	print("-outdir <dir> To specify an output directory. Default is grids in cwd.")
	print("-use_local to report to local datasource.")
	sys.exit()

def main(args):
	if len(args)<3:
		usage()
	print("Running %s (a wrapper of 'page') at %s" %(os.path.basename(args[0]),time.asctime()))
	lasname=args[1]
	if "-cs" in args:
		try:
			cs=float(args[args.index("-cs")+1])
		except Exception,e:
			print(str(e))
			usage()
	else:
		cs=CELL_SIZE #default
	ncols_f=TILE_SIZE/cs
	ncols=int(ncols_f)
	nrows=ncols  #tiles are square (for now)
	if ncols!=ncols_f:
		print("TILE_SIZE: %d must be divisible by cell size..." %(TILE_SIZE))
		usage()
	print("Using cell size: %.2f" %cs)
	if "-outdir" in args:
		outdir=args[args.index("-outdir")+1]
	else:
		outdir=GRIDS_OUT
	if not os.path.exists(outdir):
		os.mkdir(outdir)
	kmname=get_1km_name(lasname)
	try:
		N,E=kmname.split("_")[1:]
		N=int(N)
		E=int(E)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		ds_lake=None
		return 1
	xll=E*1e3
	yll=N*1e3
	xllcorner=xll+0.5*cs
	yllcorner=yll+0.5*cs
	#Specify arguments to page...
	grid_params=PAGE_GRID_FRMT.format(yllcorner,xllcorner,ncols,nrows,cs)
	predict_params=[PAGE_PREDICTOR_SWITCH,PAGE_PREDICTOR_FRMT.format(cs*2.0)]
	outname_base="page_"+os.path.splitext(os.path.basename(lasname))[0]+".asc"
	for name,pargs in [("terrain_",PAGE_TERRAIN_ARGS),("surface_",PAGE_SURFACE_ARGS)]:
		outname=os.path.join(outdir,name+outname_base)
		print("Reading %s, writing %s" %(lasname,outname))
		page_args=pargs+predict_params+["-o",outname,"-g",grid_params,lasname]
		print("Calling page like this:\n{0:s}".format(str(page_args)))
		rc,stdout,stderr=run_command(page_args)
		if stdout is not None:
			print(stdout)
		if stderr is not None:
			print(stderr)
		if rc!=0:
			print("Something wrong, return code: %d" %rc)
	return rc
	

if __name__=="__main__":
	main(sys.argv)