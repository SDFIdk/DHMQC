import sys,os,time
import  thatsDEM.dhmqc_constants as constants
from argparse import ArgumentParser
import math
import glob
import numpy as np
from subprocess import call
from thatsDEM import pointcloud
from osgeo import osr


#Call from qc_warp with this command line: "python qc_wrap.py dem_gen d:\temp\slet\raa\*.las -targs "D://temp//slet//output" "

#gridsize of the hillshade (always 0.4 m)
gridsize = 0.4

cut_terrain=[2,9,17]
bufbuf = 200
SIZE_LIM=38000000  #size limit for when to apply thinning
DEN_CUT_TERRAIN=9.0  #The cut density for when to start filtering
ZLIM_TERRAIN=0.3 #The cut z-limit for when something os deemed a local extrema which should be kept
DEN_CUT_SURFACE=13  #The cut density for when to start filtering
ZLIM_SURFACE=0.3 #The cut z-limit for when something os deemed a local extrema which should be kept
EPSG_CODE=25832 #default srs
SRS=osr.SpatialReference()
SRS.ImportFromEPSG(EPSG_CODE)
SRS_WKT=SRS.ExportToWkt()
SRS_PROJ4=SRS.ExportToProj4()
ND_VAL=-9999

progname=os.path.basename(__file__)
parser=ArgumentParser(description="Generate DSM and DTM for a las file. Will try to read surrounding tiles for buffer.",prog=progname)
parser.add_argument("-size_lim",type=int,default=SIZE_LIM,help="Specify a size limit for when to start thinning. Defaults to %d points" %SIZE_LIM)
parser.add_argument("las_file",help="Directory of las files e.g. c:\\mydir\\*.las")
parser.add_argument("output_dir",help="Where to store the hillshade e.g. c:\\final_resting_place\\")

def usage():
	parser.print_help()
		
def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	lasfolder = os.path.dirname(lasname)
	kmname=constants.get_tilename(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	print("Size limit is : %d" %pargs.size_lim)
	print("Using default srs: %s" %(SRS_PROJ4))
	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	
	center_x=(extent[2]+extent[0])*0.5
	center_y=(extent[3]+extent[1])*0.5
	
	extent_buf=extent+(-bufbuf,-bufbuf,bufbuf,bufbuf)
	print(str(extent_buf))
	
	basisname,extname=os.path.splitext(os.path.basename(lasname))
	terrainname=os.path.join(pargs.output_dir,"dtm_"+basisname+".tif")
	#There can be e,g. a "pre" in front of the tilename - get that
	prename="" 
	i=basisname.find(kmname)
	if i>0:
		prename=basisname[:i]
	if os.path.exists(terrainname):
		print(terrainname+" already exists... exiting...")
		return 1
	

	pcA={}
	for j in range(-1, 2):
		for i in range(-1, 2): 
			aktFnam=prename+constants.point_to_tilename(center_x+i*constants.tile_size,center_y-j*constants.tile_size)+extname # array indexing: neg. j is 'up'
			aktFnam=os.path.join(lasfolder,aktFnam)
			print("Offset x:%d,y:%d, reading: %s" %(i,j,aktFnam))
			if os.path.exists(aktFnam):
				#cls cut will work as long as cut_terrain is a subset of cut_surface
				pcA[(i,j)]=pointcloud.fromLAS(aktFnam).cut_to_box(*extent_buf).cut_to_class(cut_terrain)
			else:
				print("Neighbour (%d,%d) does not exist." %(i,j))

	print("done reading")
	if pcA[(0,0)].get_size()<2:
		print("Few points in tile - wont grid...")
		return 2
	#Do terrain first
	bufpc=pcA[(0,0)] 
	for key in pcA:
		if key!=(0,0):
			tc=pcA[key]
			print key
			if tc.get_size()>0:
				bufpc.extend(tc)
				print bufpc.get_size()
			
	print("Bounds for bufpc: %s" %(str(bufpc.get_bounds())))
	if bufpc.get_size()>3:
		print "triangulating terrain"
		if bufpc.get_size()>pargs.size_lim:
			print("Many points! Filtering...")
			bufpc.sort_spatially(2*gridsize)
			M=bufpc.thinning_filter(gridsize,DEN_CUT_TERRAIN,ZLIM_TERRAIN)
			bufpc=bufpc.cut(M)
			print("New number of points: %d" %bufpc.get_size())
			print("New bounds for bufpc: %s" %(str(bufpc.get_bounds())))
			del M
		bufpc.triangulate()
		g=bufpc.get_grid(x1=extent[0],x2=extent[2],y1=extent[1],y2=extent[3],cx=gridsize,cy=gridsize,nd_val=ND_VAL)
		g.grid=g.grid.astype(np.float32)
		if (g.grid==ND_VAL).all():
			return 3
		del bufpc
		g.save(terrainname, dco=["TILED=YES","COMPRESS=DEFLATE","PREDICTOR=3","ZLEVEL=9"],srs=SRS_WKT)
		#delete grid from memory to save RAM...
		del g
	
	
	return 0

	
	
if __name__=="__main__":
	main(sys.argv)
	
