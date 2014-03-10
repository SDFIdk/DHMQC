import os,sys
import time
import subprocess
import numpy as np
from osgeo import gdal,ogr
from thatsDEM import report
from utils.names import get_1km_name
DEBUG="-debug" in sys.argv
if DEBUG:
	import matplotlib
	matplotlib.use("Qt4Agg")
	import matplotlib.pyplot as plt
#-b decimin signals that returnval is min_density*10, -p
PAGE_ARGS=[os.path.join("lib","page"),"-F","Rlast","-p","boxdensity:50"]
PAGE_GRID_FRMT="G/{0:.2f}/{1:.2f}/10/10/100/-9999"
CELL_SIZE=100  #100 m cellsize in density grid
TILE_SIZE=1000  #yep - its 1km tiles...
GRIDS_OUT="density_grids"  #due to the fact that this is being called from qc_wrap it is easiest to have a standard folder for output...
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
	print("Simple wrapper of 'page'")
	print("To run:")
	print("%s <las_tile> <lake_polygon_file> (options)" %(os.path.basename(sys.argv[0])))
	print("Options:")
	print("-use_local to report to local datasource.")
	print("-debug to plot grids.")
	sys.exit()

def main(args):
	if len(args)<3:
		usage()
	print("Running %s (a wrapper of 'page') at %s" %(os.path.basename(args[0]),time.asctime()))
	lasname=args[1]
	lakename=args[2]
	use_local="-use_local" in args
	ds_report=report.get_output_datasource(use_local)
	if use_local:
		print("Using local data source for reporting.")
	else:
		print("Using global data source for reporting.")
	if ds_report is None:
		print("Failed to open report datasource - you might need to CREATE one...")
	if not os.path.exists(GRIDS_OUT):
		os.mkdir(GRIDS_OUT)
	outname_base="density_"+os.path.splitext(os.path.basename(lasname))[0]+".asc"
	outname=os.path.join(GRIDS_OUT,outname_base)
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
	xllcorner=xll+0.5*CELL_SIZE
	yllcorner=yll+0.5*CELL_SIZE
	grid_params=PAGE_GRID_FRMT.format(yllcorner,xllcorner)
	page_args=PAGE_ARGS+["-o",outname,"-g",grid_params,lasname]
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
		print("Number of no-data densities: %d" %(nd_mask.sum()))
		print("Number of lake cells       : %d"  %(lake_mask.sum()))
		den=den_grid[np.logical_not(lake_mask)].min()
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
	wkt="POLYGON(({0:.2f} {1:.2f},".format(xll,yll)
	for dx,dy in ((0,1),(1,1),(1,0)):
		wkt+="{0:.2f} {1:.2f},".format(xll+dx*TILE_SIZE,yll+dy*TILE_SIZE)
	wkt+="{0:.2f} {1:.2f}))".format(xll,yll)
	ds_lake=None
	report.report_density(ds_report,kmname,den,wkt_geom=wkt)
	return rc
	


if __name__=="__main__":
	main(sys.argv)