# Copyright (c) 2015-2016, Danish Geodata Agency <gst@gst.dk>
# Copyright (c) 2016, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
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

