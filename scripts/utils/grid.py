#quick'n dirty las-file to grid - will save geotif if gdal is installed - otherwise a npy file is saved...
#simlk, sep. 2013
import sys,os,time
import triangle
import slash
import numpy as np
try:
	from osgeo import gdal
except:
	HAS_GDAL=False
else:
	HAS_GDAL=True
def Usage():
	print("%s <las_file> <out_file> <x1> <x2> <y1> <y2> <ncols> <nrows>" %os.path.basename(sys.argv[0]))
	sys.exit()

def WriteRaster(fname,A,geo,dtype=None,nd_value=None,colortable=None):
	if dtype is None:
		dtype=gdal.GDT_Float32
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
	if len(args)<9:
		Usage()
	lasfile=args[1]
	outfile=args[2]
	gx1,gx2,gy1,gy2=map(float,args[3:7])
	ncols,nrows=map(int,args[7:9])
	tall=0
	print("Loading point cloud from %s" %lasfile)
	t1=time.clock()
	lasp=slash.LasFile(lasfile)
	xy,z,c=lasp.read_records()
	#I=np.where(c==2)[0]
	#xy=xy[I]
	#z=z[I]
	#c=c[I]
	print xy.shape, xy.flags
	lasp.close()
	t2=time.clock()
	t3=t2-t1
	print("Reading ALL data took %.4f s" %t3)
	tall+=t3
	x1,y1=np.min(xy,axis=0)
	x2,y2=np.max(xy,axis=0)
	print("Extent of point cloud: %.2f %.2f %.2f %.2f" %(x1,y1,x2,y2))
	print("Z: %.2f, %.2f mean: %.2f" %(z.min(),z.max(),z.mean()))
	csx=(gx2-gx1)/float(ncols)
	csy=(gy2-gy1)/float(nrows)
	geo_ref=[gx1,csx,0,gy2,0,-csy] #geo_ref gdal style...
	print("Grid cell sizes x: %.6f y: %.6f" %(csx,csy))
	print("*"*70)
	print("Building triangulation and index...")
	t1=time.clock()
	tri=triangle.Triangulation(xy)
	t2=time.clock()
	t3=t2-t1
	print("TIN'ing took %.3f s" %t3)
	tall+=t3
	print("*"*70)
	print("Gridding...")
	t1=time.clock()
	grid=tri.make_grid(z,ncols,nrows,gx1,csx,gy2,csy)
	t2=time.clock()
	t3=t2-t1
	print("Gridding (  %s  ) took %.3f s" %(grid.shape,t3))
	tall+=t3
	print("All in all: %.3f s" %tall)
	print("Grid z: %.2f, %.2f, mean: %.2f" %(grid.min(),grid.max(),grid.mean()))
	outfile=os.path.splitext(outfile)[0]
	grid=grid.astype(np.float32)
	if HAS_GDAL:
		outfile+=".tif"
		WriteRaster(outfile,grid,nd_value=-999)
	else:
		print("Unable to load gdal - saving as npy grid...")
		geo_ref_name=outfile+"_georef.txt"
		outfile+=".npy"
		print("Saving %s" %outfile)
		np.save(outfile,grid)
		print("Saving geo reference as %s" %geo_ref_name)
		np.savetxt(geo_ref_name,geo_ref)
		
	
if __name__=="__main__":
	main(sys.argv)
	