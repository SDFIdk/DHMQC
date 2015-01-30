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
##########################
## Polygonize building points from LAS
## Includes a 4 liner fast density grid creation!! Nice :-)
##########################
import os,sys
import time
import numpy as np
import thatsDEM.dhmqc_constants as constants
from osgeo import gdal,ogr
from thatsDEM import pointcloud,report
from utils.osutils import ArgumentParser

DEBUG="-debug" in sys.argv
if DEBUG:
	import matplotlib
	matplotlib.use("Qt4Agg")
	import matplotlib.pyplot as plt
b_class=constants.building
TILE_SIZE=constants.tile_size #1km blocks
dst_fieldname='DN'
default_min_z = -999999999
default_max_z =  999999999


progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Polygonize areas with points of a specific class (typically buildings) OR above a specific height.",prog=progname)
parser.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
#add some arguments below
group = parser.add_mutually_exclusive_group()
group.add_argument("-class",dest="cut_to",type=int,default=b_class,help="Inspect points of this class - defaults to 'building'")
group.add_argument("-height",type=float,help="Specify the cut off height.")
parser.add_argument("las_file",help="input las tile.")


def usage():
	parser.print_help()

def usage():
	print("Call:\n%s <las_file> -class <class>|-height <height> -use_local" %os.path.basename(sys.argv[0]))
	print("Use -class <class> to restrict to a specified class - defaults to 'building'")
	print("Use -height <height> to restrict to a specified minimum height (to detect clouds)")
	print("")
	print("     NOTE: Use EITHER -class or -height. ")
	print("")
	print("Use -use_local to force output to local database.")
	

def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	use_local=pargs.use_local
	if pargs.height is not None:
		reporter=report.ReportClouds(use_local)
		CS=4
		CELL_COUNT_LIM=4
	else:
		reporter=report.ReportAutoBuilding(use_local)
		CS=1
		CELL_COUNT_LIM=2
	kmname=constants.get_tilename(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	try:
		xul,yll,xlr,yul=constants.tilename_to_extent(kmname)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file name: %s" %lasname)
		return 1
	if pargs.height is not None:
		print("Cutting to z above %.2f m" %(pargs.height))
		pc=pointcloud.fromLAS(lasname).cut_to_z_interval(pargs.height,default_max_z)
	else:
		print("Cutting to class %d" %pargs.cut_to)
		pc=pointcloud.fromLAS(lasname).cut_to_class(pargs.cut_to)
	
	if pc.get_size()==0:
		print("No points after restriction...")
		return 0
	
	cs=CS
	ncols=TILE_SIZE/cs
	nrows=ncols
	georef=[xul,cs,0,yul,0,-cs]
	arr_coords=((pc.xy-(georef[0],georef[3]))/(georef[1],georef[5])).astype(np.int32)
	M=np.logical_and(arr_coords[:,0]>=0, arr_coords[:,0]<ncols)
	M&=np.logical_and(arr_coords[:,1]>=0,arr_coords[:,1]<nrows)
	arr_coords=arr_coords[M]
	# Wow - this gridding is sooo simple! and fast!
	#create flattened index
	B=arr_coords[:,1]*ncols+arr_coords[:,0]
	bins=np.arange(0,ncols*nrows+1)
	h,b=np.histogram(B,bins)
	print h.shape,h.max(),h.min()
	h=h.reshape((nrows,ncols))
	if DEBUG:
		plt.imshow(h)
		plt.show()
	M=(h>=CELL_COUNT_LIM).astype(np.uint8)
	#Now create a GDAL memory raster
	mem_driver=gdal.GetDriverByName("MEM")
	mask_ds=mem_driver.Create("dummy",int(M.shape[1]),int(M.shape[0]),1,gdal.GDT_Byte)
	mask_ds.SetGeoTransform(georef)
	mask_ds.GetRasterBand(1).WriteArray(M) #write zeros to output
	#Ok - so now polygonize that - use the mask as ehem... mask...
	m_drv=ogr.GetDriverByName("Memory")
	ds = m_drv.CreateDataSource( "dummy")
	if ds is None:
		print "Creation of output ds failed.\n"
		return
	lyr = ds.CreateLayer( "polys", None, ogr.wkbPolygon)
	fd = ogr.FieldDefn( dst_fieldname, ogr.OFTInteger )
	lyr.CreateField( fd )
	dst_field = 0
	print("Polygonizing.....")
	gdal.Polygonize(mask_ds.GetRasterBand(1), mask_ds.GetRasterBand(1), lyr, dst_field)
	lyr.ResetReading()
	nf=lyr.GetFeatureCount()
	for i in xrange(nf):
		fet=lyr.GetNextFeature()
		geom=fet.GetGeometryRef()
		reporter.report(kmname,ogr_geom=geom)
	return 0
		
		
	
	

if __name__=="__main__":
	main(sys.argv)
	
	