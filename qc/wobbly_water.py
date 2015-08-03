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
######################################################################################
## Test for water that aint flat (by using mean filter)
##
######################################################################################
import sys,os,time
#import some relevant modules...
from osgeo import gdal,ogr
from thatsDEM import pointcloud, vector_io, array_geometry
from db import report
from math import tan,radians
import numpy as np
import  dhmqc_constants as constants
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)

cut_to=constants.water
zmin=0.2
frad=1.0 #filter radius
cs=2.0  #default cell-size for polygonisation
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Find steep triangles (in water class by default). Large triangles will be ignored...",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
#add some arguments below
parser.add_argument("-class",dest="cut_to",type=int,default=cut_to,help="Inspect points of this class - defaults to 'water'")
parser.add_argument("-zmin",type=float,default=zmin,help="Specify minimal z-distance to mean for a point that isn't flat. Defaults to %.2f m" %zmin)
parser.add_argument("-frad",type=float,default=frad,help="Specify the filtering radius in which to calculate mean. Defaults to %.2f m" %frad)
parser.add_argument("las_file",help="input las tile.")



#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
def usage():
	parser.print_help()
	

def polygonise_points(pc,cs,cell_count_lim=1):
	x1,y1,x2,y2=pc.get_bounds()
	x1-=cs
	y2+=cs
	ncols=int(float((x2-x1))/cs)+1
	nrows=int(float((y2-y1))/cs)+1
	georef=[x1,cs,0,y2,0,-cs]
	arr_coords=((pc.xy-(georef[0],georef[3]))/(georef[1],georef[5])).astype(np.int32)
	M=np.logical_and(arr_coords[:,0]>=0, arr_coords[:,0]<ncols)
	M&=np.logical_and(arr_coords[:,1]>=0,arr_coords[:,1]<nrows)
	arr_coords=arr_coords[M]
	# Wow - this gridding is sooo simple! and fast!
	#create flattened index
	B=arr_coords[:,1]*ncols+arr_coords[:,0]
	bins=np.arange(0,ncols*nrows+1)
	h,b=np.histogram(B,bins)
	h=h.reshape((nrows,ncols))
	M=(h>=cell_count_lim).astype(np.uint8)
	#Now create a GDAL memory raster
	mem_driver=gdal.GetDriverByName("MEM")
	mask_ds=mem_driver.Create("dummy",int(M.shape[1]),int(M.shape[0]),1,gdal.GDT_Byte)
	mask_ds.SetGeoTransform(georef)
	mask_ds.GetRasterBand(1).WriteArray(M) #write zeros to output
	#Ok - so now polygonize that - use the mask as ehem... mask...
	m_drv=ogr.GetDriverByName("Memory")
	ds = m_drv.CreateDataSource( "dummy")
	if ds is None:
		print("Creation of output ds failed.")
		return
	dst_field="DN"
	lyr = ds.CreateLayer( "polys", None, ogr.wkbPolygon)
	fd = ogr.FieldDefn(dst_field, ogr.OFTInteger )
	lyr.CreateField( fd )
	dst_field = 0
	print("Polygonizing.....")
	gdal.Polygonize(mask_ds.GetRasterBand(1), mask_ds.GetRasterBand(1), lyr, dst_field)
	lyr.ResetReading()
	return ds,lyr

def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception,e:
		print(str(e))
		return 1
	lasname=pargs.las_file
	kmname=constants.get_tilename(lasname)
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportWobbly(pargs.use_local)
	pc=pointcloud.fromAny(lasname).cut_to_class(pargs.cut_to)
	print("%d points of class %d in this tile..." %(pc.get_size(),pargs.cut_to))
	if pc.get_size()<3:
		print("Few points of class %d in this tile..." %pargs.cut_to)
		return 0
	print("Using z-limit %.2f m" %pargs.zmin)
	pc.sort_spatially(pargs.frad)
	meanz=pc.mean_filter(pargs.frad)
	diff=pc.z-meanz
	M=(np.fabs(diff)>pargs.zmin)
	n=M.sum()
	print("Found %d wobbly points" %n)
	if n>0:
		pc=pc.cut(M)
		diff=diff[M]
		ds,lyr=polygonise_points(pc,2*pargs.frad,1)
		nf=lyr.GetFeatureCount()
		for i in xrange(nf):
			fet=lyr.GetNextFeature()
			geom=fet.GetGeometryRef()
			arr_geom=array_geometry.ogrpoly2array(geom,flatten=True)
			N=array_geometry.points_in_polygon(pc.xy,arr_geom)
			n=N.sum()
			if n>0:
				d=diff[N]
				m1=d.min()
				m2=d.max()
				
			else:
				m1=-999
				m2=-999
				
			reporter.report(kmname,pargs.cut_to,pargs.frad,n,m1,m2,ogr_geom=geom)
		
		
		
	return 0
	
	
	
	
		

#to be able to call the script 'stand alone'
if __name__=="__main__":
	main(sys.argv)