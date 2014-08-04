import os,sys
import time
import subprocess
import numpy as np
from osgeo import gdal,ogr
from thatsDEM import report
from utils.names import get_1km_name
import math
ALL_LAKE=-2 #signal density that all is lake...
DEBUG="-debug" in sys.argv
if DEBUG:
	import matplotlib
	matplotlib.use("Qt4Agg")
	import matplotlib.pyplot as plt
#-b decimin signals that returnval is min_density*10, -p
PAGE=os.path.join(os.path.dirname(__file__),"lib","page")
PAGE_ARGS=[PAGE,"-S","Rlast"]
PAGE_PREDICTOR_SWITCH="-p"
PAGE_PREDICTOR_FRMT="distance:{0:.0f}"
PAGE_GRID_FRMT="G/{0:.2f}/{1:.2f}/{2:.0f}/{3:.0f}/{4:.4f}/-9999"
CELL_SIZE=100.0  #100 m cellsize in density grid
TILE_SIZE=1000  #yep - its 1km tiles...
GRIDS_OUT="distance_grids"  #due to the fact that this is being called from qc_wrap it is easiest to have a standard folder for output...
#input arguments as a list.... Popen will know what to do with it....
def run_command(args):
	prc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
	stdout,stderr=prc.communicate()
	return prc.poll(),stdout,stderr


def burn_vector_layer(layer_in,georef,shape):
	mem_driver=gdal.GetDriverByName("MEM")
	mask_ds=mem_driver.Create("dummy",int(shape[1]),int(shape[0]),1,gdal.GDT_Byte)
	mask_ds.SetGeoTransform(georef)
	mask=np.zeros(shape,dtype=np.bool)
	mask_ds.GetRasterBand(1).WriteArray(mask) #write zeros to output
	#mask_ds.SetProjection('LOCAL_CS["arbitrary"]')
	ok=gdal.RasterizeLayer(mask_ds,[1],layer_in,burn_values=[1],options=['ALL_TOUCHED=TRUE'])
	A=mask_ds.ReadAsArray()
	return A


def usage():
	print("Simple wrapper of 'page' with distance predictor.")
	print("To run:")
	print("%s <las_tile> <lake_polygon_file> (options)" %(os.path.basename(sys.argv[0])))
	print("Options:")
	print("-cs <cell_size> to specify cell size of grid. Default 100 m (TILE_SIZE must be divisible by cs)")
	print("-outdir <dir> To specify an output directory. Default is distance_grids in cwd.")
	print("-use_local to report to local datasource.")
	print("-debug to plot grids.")
	sys.exit()

def main(args):
	if len(args)<3:
		usage()
	print("Running %s (a wrapper of 'page') at %s" %(os.path.basename(args[0]),time.asctime()))
	lasname=args[1]
	lakename=args[2]
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
	use_local="-use_local" in args
	#reporter=report.ReportDensity(use_local)
	if "-outdir" in args:
		outdir=args[args.index("-outdir")+1]
	else:
		outdir=GRIDS_OUT
	if not os.path.exists(outdir):
		os.mkdir(outdir)
	outname_base="dist_{0:.0f}_".format(cs)+os.path.splitext(os.path.basename(lasname))[0]+".asc"
	outname=os.path.join(outdir,outname_base)
	ds_lake=ogr.Open(lakename)
	layer=ds_lake.GetLayer(0)
	print("Reading %s, writing %s" %(lasname,outname))
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
	boxden_params=[PAGE_PREDICTOR_SWITCH,PAGE_PREDICTOR_FRMT.format(math.ceil(cs*2.0))]
	page_args=PAGE_ARGS+boxden_params+["-o",outname,"-g",grid_params,lasname]
	print("Calling page like this:\n{0:s}".format(str(page_args)))
	rc,stdout,stderr=run_command(page_args)
	if stdout is not None:
		print(stdout)
	if stderr is not None:
		print(stderr)
	if rc==0:
		ds_grid=gdal.Open(outname)
		georef=ds_grid.GetGeoTransform()
		nd_val=ds_grid.GetRasterBand(1).GetNoDataValue()
		den_grid=ds_grid.ReadAsArray()
		ds_grid=None
		lake_mask=burn_vector_layer(layer,georef,den_grid.shape)
		#what to do with nodata??
		nd_mask=(den_grid==nd_val)
		den_grid[den_grid==nd_val]=0
		n_lake=lake_mask.sum()
		print("Number of no-data densities: %d" %(nd_mask.sum()))
		print("Number of lake cells       : %d"  %(n_lake))
		if n_lake<den_grid.size:
			not_lake=den_grid[np.logical_not(lake_mask)]
			den=not_lake.min()
			mean_den=not_lake.mean()
			
		else:
			den=ALL_LAKE
			mean_den=ALL_LAKE
		print("Minumum density            : %.2f" %den)
		if DEBUG:
			plt.figure()
			plt.subplot(1,2,1)
			im=plt.imshow(den_grid)
			plt.colorbar(im)
			plt.subplot(1,2,2)
			plt.imshow(lake_mask)
			plt.show()
	else:
		print("Something wrong, return code: %d" %rc)
		den=-1
		mean_den=-1
	wkt="POLYGON(({0:.2f} {1:.2f},".format(xll,yll)
	for dx,dy in ((0,1),(1,1),(1,0)):
		wkt+="{0:.2f} {1:.2f},".format(xll+dx*TILE_SIZE,yll+dy*TILE_SIZE)
	wkt+="{0:.2f} {1:.2f}))".format(xll,yll)
	ds_lake=None
	#reporter.report(kmname,den,mean_den,cs,wkt_geom=wkt)
	return rc
	

if __name__=="__main__":
	main(sys.argv)