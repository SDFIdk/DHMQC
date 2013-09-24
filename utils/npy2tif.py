import os,sys
from osgeo import gdal
import numpy as np
def WriteRaster(fname,A,geo,dtype=gdal.GDT_Float32,nd_value=None,colortable=None):
	gdal.AllRegister()
	driver=gdal.GetDriverByName("GTiff")
	if os.path.exists(fname):
		try:
			driver.Delete(fname)
		except Exception, msg:
			print msg
		else:
			print("Overwriting %s..." %fname)
	else:
		print("Saving %s..."%fname)
	
	dst_ds=driver.Create(fname,A.shape[1],A.shape[0],1,dtype)
	dst_ds.SetGeoTransform(geo)
	band=dst_ds.GetRasterBand(1)
	if nd_value is not None:
		band.SetNoDataValue(nd_value)
	band.WriteArray(A)
	dst_ds=None

def main(args):
	grid=np.load(args[1]).astype(np.float32)
	geo_ref_name=args[2]
	outname=args[3]
	geo_ref=np.loadtxt(geo_ref_name)
	WriteRaster(outname,grid,geo_ref,nd_value=-999)
	

if __name__=="__main__":
	main(sys.argv)
	