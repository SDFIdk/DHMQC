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
import sys,os,time
import  thatsDEM.dhmqc_constants as constants
from argparse import ArgumentParser
import math
import glob
import numpy as np
from subprocess import call
from thatsDEM import pointcloud, grid
from osgeo import gdal,osr
from math import ceil
import sqlite3
GEOID_GRID=os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b_utm32.tif")
#Call from qc_warp with this command line: "python qc_wrap.py dem_gen d:\temp\slet\raa\*.las -targs "D://temp//slet//output" "

#gridsize of the hillshade (always 0.4 m)
gridsize = 0.4
#IMPORTANT: IF TERRAINCLASSES ARE NOT A SUBSET OF SURFCLASSES - CHANGE SOME LOGIC BELOW!!! 
cut_terrain=[2,9,17]
cut_surface=[2,3,4,5,6,9,17]
bufbuf = 200
EPSG_CODE=25832 #default srs
SRS=osr.SpatialReference()
SRS.ImportFromEPSG(EPSG_CODE)
SRS_WKT=SRS.ExportToWkt()
SRS_PROJ4=SRS.ExportToProj4()
ND_VAL=-9999

progname=os.path.basename(__file__)
parser=ArgumentParser(description="Generate DTM for a las file. Will try to read surrounding tiles for buffer.",prog=progname)
parser.add_argument("-overwrite",action="store_true",help="Overwrite output file if it exists. Default is to skip the tile.")
parser.add_argument("-dsm",action="store_true",help="Also generate a dsm.")
parser.add_argument("-nodtm",action="store_true",help="Do not generate a dtm.")
parser.add_argument("-nowarp",action="store_true",help="Do NOT warp output grid to dvr90.")
parser.add_argument("-debug",action="store_true",help="Debug - for now only saves resampled geoid also.")
parser.add_argument("las_file",help="Input las tile (the important bit is tile name).")
parser.add_argument("tile_db",help="Input sqlite db containing tiles. See tile_coverage.py. las_file should point to a sub-tile of the db.")
parser.add_argument("output_dir",help="Where to store the hillshade e.g. c:\\final_resting_place\\")

def usage():
	parser.print_help()


def resample_geoid(extent,cx,cy):
	ds=gdal.Open(GEOID_GRID)
	georef=ds.GetGeoTransform()
	xoff=max(int((extent[0]-georef[0])/georef[1])-1,0)
	yoff=max(int((extent[3]-georef[3])/georef[5])-1,0)
	xwin=min(int(ceil((extent[2]-extent[0])/georef[1]))+3,ds.RasterXSize-xoff)
	ywin=min(int(ceil((extent[1]-extent[3])/georef[5]))+3,ds.RasterYSize-yoff)
	band=ds.GetRasterBand(1)
	nd_val=band.GetNoDataValue()
	G=band.ReadAsArray(xoff,yoff,xwin,ywin).astype(np.float64)
	ncols=int(ceil((extent[2]-extent[0])/cx))
	nrows=int(ceil((extent[3]-extent[1])/cy))
	geo_ref_geoid=[georef[0]+(xoff+0.5)*georef[1],georef[1],georef[3]+(yoff+0.5)*georef[5],-georef[5]] #translate from GDAL-style georef
	geo_ref_out=[extent[0]+0.5*cx,cx,extent[3]-0.5*cy,cy] #translate from GDAL-style georef
	A=grid.resample_grid(G,nd_val,geo_ref_geoid,geo_ref_out,ncols,nrows)
	assert((A!=nd_val).all())
	return A
	

def gridit(pc,extent,outname,g_warp=None):
	pc.triangulate()
	g=pc.get_grid(x1=extent[0],x2=extent[2],y1=extent[1],y2=extent[3],cx=gridsize,cy=gridsize,nd_val=ND_VAL)
	M=(g.grid!=ND_VAL)
	if not M.any():
		return 3
	if g_warp is not None:
		g.grid[M]-=g_warp[M]  #warp to dvr90
	g.grid=g.grid.astype(np.float32) #only downcast
	g.save(outname, dco=["TILED=YES","COMPRESS=DEFLATE","PREDICTOR=3","ZLEVEL=9"],srs=SRS_WKT)
	#delete grid from memory to save RAM...
	del g
	return 0
		
def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	kmname=constants.get_tilename(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	print("Using default srs: %s" %(SRS_PROJ4))
	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	extent_buf=extent+(-bufbuf,-bufbuf,bufbuf,bufbuf)
	terrainname=os.path.join(pargs.output_dir,"dtm_"+kmname+".tif")
	surfacename=os.path.join(pargs.output_dir,"dsm_"+kmname+".tif")
	terrain_exists=os.path.exists(terrainname)
	surface_exists=os.path.exists(surfacename)
	if pargs.nodtm:
		do_dtm=False
	else:
		do_dtm=pargs.overwrite or  (not terrain_exists)
	if pargs.dsm:
		do_dsm=pargs.overwrite or  (not surface_exists)
	else:
		do_dsm=False
	if not (do_dtm or do_dsm):
		print("dtm already exists: %s" %terrain_exists)
		print("dsm already exists: %s" %surface_exists)
		print("Nothing to do - exiting...")
		return 2
	con=sqlite3.connect(pargs.tile_db)
	cur=con.cursor()
	cur.execute("select row,col from coverage where tile_name=?",(kmname,))
	data=cur.fetchone()
	if data is None:
		print("Tile %s does not exist!" %kmname)
		return -1
	#will raise an exception if the tile_name is not in the db!!!
	row,col=data
	cur.execute("select path,row,col from coverage where abs(row-?)<2 and abs(col-?)<2",(row,col))
	tiles=cur.fetchall()
	cur.close()
	con.close()
	bufpc=None
	for aktFnam,r,c in tiles:
		i=r-row
		j=c-col
		print("Offset x:%d, y:%d, reading: %s" %(j,i,aktFnam))
		if os.path.exists(aktFnam):
			pc=pointcloud.fromAny(aktFnam,include_return_number=True).cut_to_box(*extent_buf).cut_to_class(cut_surface) #works as long cut_terrain is a subset of cut_surface...!!!!
			if pc.get_size()>0:
				if bufpc is None:
					bufpc=pc
				else:
					bufpc.extend(pc)
			del pc
		else:
			print("Neighbour (%d,%d) does not exist." %(i,j))
	if bufpc is None:
		return 3
	print("done reading")
	print("Bounds for bufpc: %s" %(str(bufpc.get_bounds())))
	print("# all points: %d" %(bufpc.get_size()))
	if bufpc.get_size()>3:
		rc1=0
		rc2=0
		if not pargs.nowarp:
			G=resample_geoid(extent,gridsize,gridsize)
			if pargs.debug:
				G_name=os.path.join(pargs.output_dir,"geoid_"+kmname+".tif")
				gg=grid.Grid(G,[extent[0],gridsize,0,extent[3],0,-gridsize])
				gg.save(G_name,dco=["TILED=YES","COMPRESS=LZW"])
		else:
			G=None
		if do_dtm:
			terr_pc=bufpc.cut_to_class(cut_terrain)
			if terr_pc.get_size()>3:
				print("Doing terrain")
				rc1=gridit(terr_pc,extent,terrainname,G)
			else:
				rc1=3
			del terr_pc
		if do_dsm:
			surf_pc=bufpc.cut_to_return_number(1)
			del bufpc
			if surf_pc.get_size()>3:
				print("Doing surface")
				rc2=gridit(surf_pc,extent,surfacename,G)
			else:
				rc2=3
			del surf_pc
				
		return max(rc1,rc2)
	else:	
		return 3
	
	

	
	
if __name__=="__main__":
	main(sys.argv)
	
