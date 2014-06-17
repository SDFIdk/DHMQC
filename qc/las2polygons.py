##########################
## Polygonize building points from LAS
## Includes a 4 liner fast density grid creation!! Nice :-)
##########################
import os,sys
import time
import numpy as np
import dhmqc_constants as constants
from osgeo import gdal,ogr
from thatsDEM import pointcloud
from utils.names import get_1km_name
DEBUG="-debug" in sys.argv
if DEBUG:
	import matplotlib
	matplotlib.use("Qt4Agg")
	import matplotlib.pyplot as plt
b_class=constants.building
TILE_SIZE=1e3   #1km blocks
CS=1  #do a 1000,1000 grid with 1m cells
CELL_COUNT_LIM=2  #at least this pts pr. cell to include it...
dst_fieldname='DN'
def usage():
	print("Call:\n%s <las_file> <polygon_file_out> -class <class>" %os.path.basename(sys.argv[0]))
	print("Use -class <class> to restrict to a specified class - defaults to 'building'")
	sys.exit()

def main(args):
	if len(args)<3:
		usage()
	lasname=args[1]
	outname=args[2]
	kmname=get_1km_name(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	try:
		N,E=kmname.split("_")[1:]
		N=int(N)
		E=int(E)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file name: %s" %lasname)
		return 1
	if "-class" in args:
		i=args.index("-class")
		cr=int(args[i+1])
	else:
		cr=b_class
	pc=pointcloud.fromLAS(lasname).cut_to_class(cr)
	print("{0:d} points of class {1:d}".format(pc.get_size(),cr))
	cs=CS
	xll=E*1e3
	yll=N*1e3
	xul=xll
	yul=yll+TILE_SIZE
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
	shp_drv=ogr.GetDriverByName("ESRI Shapefile")
	ds = shp_drv.CreateDataSource( outname )
	if ds is None:
		print "Creation of output file failed.\n"
		return
	lyr = ds.CreateLayer( "polys", None, ogr.wkbPolygon)
	fd = ogr.FieldDefn( dst_fieldname, ogr.OFTInteger )
	lyr.CreateField( fd )
	dst_field = 0
	print("Polygonizing.....")
	gdal.Polygonize(mask_ds.GetRasterBand(1), mask_ds.GetRasterBand(1), lyr, dst_field)
	ds=None
	

if __name__=="__main__":
	main(sys.argv)
	
	