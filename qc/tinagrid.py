import os,sys
from thatsDEM import pointcloud, array_geometry,grid
from thatsDEM import dhmqc_constants as constants
import numpy as np
from osgeo import gdal


def usage():
	print("Usage:\n%s <grid_in> <grid_out>" %os.path.basename(sys.argv[0]))
	return 1

	
def main(args):
	if len(args)<3:
		return(usage())
	inname=args[1]
	outname=args[2]
	ds=gdal.Open(inname)
	geo_ref=ds.GetGeoTransform()
	nd_val=ds.GetRasterBand(1).GetNoDataValue()
	x1=geo_ref[0]
	y2=geo_ref[3]
	cx=geo_ref[1]
	cy=geo_ref[5]
	x2=x1+ds.RasterXSize*cx
	y1=y2+ds.RasterYSize*cy
	ds=None
	print("Reading grid...")
	pc=pointcloud.fromGrid(inname)
	print("Triangulating...")
	pc.triangulate()
	print("Gridding...")
	g=pc.get_grid(x1=x1,x2=x2,y1=y1,y2=y2,cx=cx,cy=-cy,nd_val=nd_val)
	g.grid=g.grid.astype(np.float32)
	g.save(outname)
	return 0


if __name__=="__main__":
	main(sys.argv)