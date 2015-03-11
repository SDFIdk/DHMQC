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
from osgeo import gdal,ogr
from thatsDEM import vector_io
from db import report
import dhmqc_constants as constants
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
import math
LIBDIR=os.path.realpath(os.path.join(os.path.dirname(__file__),"lib"))
ALL_LAKE=-2 #signal density that all is lake...
#-b decimin signals that returnval is min_density*10, -p
PAGE=os.path.join(LIBDIR,"page")
PAGE_ARGS=[PAGE,"-S","Rlast"]
PAGE_BOXDEN_FRMT="-pboxdensity:{0:.2f}"
PAGE_GRID_FRMT="-gG/{0:.2f}/{1:.2f}/{2:.0f}/{3:.0f}/{4:.4f}/-9999"
CELL_SIZE=100.0  #100 m cellsize in density grid
TILE_SIZE=constants.tile_size #should be 1km tiles...
GRIDS_OUT="density_grids"  #due to the fact that this is being called from qc_wrap it is easiest to have a standard folder for output...
#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.

progname=os.path.basename(__file__).replace(".pyc",".py")
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Write density grids of input tiles - report to db.",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
parser.add_argument("-cs",type=float,help="Specify cell size of grid. Default 100 m (TILE_SIZE must be divisible by cs)",default=CELL_SIZE)
parser.add_argument("-outdir",help="To specify an output directory. Default is "+GRIDS_OUT+" in cwd.",default=GRIDS_OUT)
#add some arguments below
parser.add_argument("-lakesql",help="Specify sql-statement for lake layer selection (e.g. for reference data in a database)")
parser.add_argument("-seasql",help="Specify sql-statement for sea layer selection (e.g. for reference data in a database)")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("ref_data",help="input reference data connection string (e.g to a db, or just a path to a shapefile).")


def usage():
	parser.print_help()

#input arguments as a list.... Popen will know what to do with it....
def run_command(args):
	prc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
	stdout,stderr=prc.communicate()
	return prc.poll(),stdout,stderr


	

def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception,e:
		print(str(e))
		return 1
	kmname=constants.get_tilename(pargs.las_file)
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	cs=pargs.cs
	ncols_f=TILE_SIZE/cs
	ncols=int(ncols_f)
	nrows=ncols  #tiles are square (for now)
	if ncols!=ncols_f:
		print("TILE_SIZE: %d must be divisible by cell size..." %(TILE_SIZE))
		usage()
		return 1
	print("Using cell size: %.2f" %cs)
	use_local=pargs.use_local
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportDensity(use_local)
	outdir=pargs.outdir
	if not os.path.exists(outdir):
		os.mkdir(outdir)
	lasname=pargs.las_file
	waterconnection=pargs.ref_data
	outname_base="den_{0:.0f}_".format(cs)+os.path.splitext(os.path.basename(lasname))[0]+".asc"
	outname=os.path.join(outdir,outname_base)
	print("Reading %s, writing %s" %(lasname,outname))
	try:
		extent=constants.tilename_to_extent(kmname)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	xll=extent[0]
	yll=extent[1]
	xllcorner=xll+0.5*cs
	yllcorner=yll+0.5*cs
	#Specify arguments to page...
	grid_params=PAGE_GRID_FRMT.format(yllcorner,xllcorner,ncols,nrows,cs)
	boxden_params=[PAGE_BOXDEN_FRMT.format(cs/2.0)]
	page_args=PAGE_ARGS+boxden_params+["-o",outname,grid_params,lasname]
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
		t1=time.clock()
		if pargs.lakesql is None and pargs.seasql is None:
			print("No layer selection specified - assuming that all water polys are in first layer of connection...!")
			lake_mask=vector_io.burn_vector_layer(waterconnection,georef,den_grid.shape,None,None)
		else:
			lake_mask=np.zeros(den_grid.shape,dtype=np.bool)
			if pargs.lakesql is not None:
				print("Burning lakes...")
				lake_mask|=vector_io.burn_vector_layer(waterconnection,georef,den_grid.shape,None,pargs.lakesql)
			if pargs.seasql is not None:
				print("Burning sea...")
				lake_mask|=vector_io.burn_vector_layer(waterconnection,georef,den_grid.shape,None,pargs.seasql)
		t2=time.clock()
		print("Burning 'water' took: %.3f s" %(t2-t1))
		#what to do with nodata??
		nd_mask=(den_grid==nd_val)
		den_grid[den_grid==nd_val]=0
		n_lake=lake_mask.sum()
		print("Number of no-data densities: %d" %(nd_mask.sum()))
		print("Number of water cells       : %d"  %(n_lake))
		if n_lake<den_grid.size:
			not_lake=den_grid[np.logical_not(lake_mask)]
			den=not_lake.min()
			mean_den=not_lake.mean()
			
		else:
			den=ALL_LAKE
			mean_den=ALL_LAKE
		print("Minumum density            : %.2f" %den)
		if False:
			plt.figure()
			plt.subplot(1,2,1)
			im=plt.imshow(den_grid)
			plt.colorbar(im)
			plt.subplot(1,2,2)
			plt.imshow(lake_mask)
			plt.show()
	else:
		#Perhaps raise an exception here??
		raise Exception("Something wrong, return code from page: %d" %rc)
	wkt=constants.tilename_to_extent(kmname,return_wkt=True)
	reporter.report(kmname,den,mean_den,cs,wkt_geom=wkt)
	return rc
	

if __name__=="__main__":
	main(sys.argv)