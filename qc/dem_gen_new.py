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
import sys,os,time
import dhmqc_constants as constants
from argparse import ArgumentParser
import math
import glob
import numpy as np
from subprocess import call
from thatsDEM import pointcloud, grid, array_geometry, vector_io
from osgeo import gdal,osr,ogr
from math import ceil,modf
import sqlite3
import scipy.ndimage as image
#REFERENCE LAYERS MUST BE DEFINED IN A SEPARATE DEFINITION FILE, FOLLOWING NAMES SHOULD BE DEFINED - could be None
#MAP_CONNECTION
#RIVER_LAYER
#BUILD_LAYER
#LAKE_LAYER
#SEA_LAYER
GEOID_GRID=os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b_utm32.tif")
#Call from qc_warp with this command line: "python qc_wrap.py dem_gen d:\temp\slet\raa\*.las -targs "D://temp//slet//output" "

#gridsize of the hillshade (always 0.4 m)
gridsize = 0.4
#IMPORTANT: IF TERRAINCLASSES ARE NOT A SUBSET OF SURFCLASSES - CHANGE SOME LOGIC BELOW!!! 
cut_terrain=[2,9,17]
cut_surface=[2,3,4,5,6,9,17]
only_surface=[3,4,5,6]
zlim=1.0 #for steep triangles towards water...
bufbuf = 200
cell_buf=20 #buffer with this amount of cells... should be larger than various smoothing radii and bufbuf>cell_buf*gridsize
EPSG_CODE=25832 #default srs
SRS=osr.SpatialReference()
SRS.ImportFromEPSG(EPSG_CODE)
SRS_WKT=SRS.ExportToWkt()
SRS_PROJ4=SRS.ExportToProj4()
ND_VAL=-9999
DSM_TRIANGLE_LIMIT=3 #LIMIT for large triangles
H_SYS="E" #default H_SYS - can be changed...
#TODO:
#HANDLE BUFFERING OF GRIDS WHEN SMOOTHING

progname=os.path.basename(__file__)
parser=ArgumentParser(description="Generate DTM for a las file. Will try to read surrounding tiles for buffer.",prog=progname)
parser.add_argument("-overwrite",action="store_true",help="Overwrite output file if it exists. Default is to skip the tile.")
parser.add_argument("-dsm",action="store_true",help="Also generate a dsm.")
parser.add_argument("-dtm",action="store_true",help="Generate a dtm.")
parser.add_argument("-triangle_limit",type=float,help="Specify triangle size limit for when to not render (and fillin from DTM.) (defaults to %.2f m)"%DSM_TRIANGLE_LIMIT,default=DSM_TRIANGLE_LIMIT)
parser.add_argument("-zlim",type=float,help="Limit for when a large wet triangle is not flat",default=zlim)
parser.add_argument("-hsys",choices=["dvr90","E"],default="dvr90",help="Output height system (E or dvr90 - default is dvr90).")
parser.add_argument("-nowarp",action="store_true",help="Do not change height system - assume same for all input tiles")
parser.add_argument("-debug",action="store_true",help="Debug - save some additional metadata grids.")
parser.add_argument("-round",action="store_true",help="Round to mm level (experimental)")
parser.add_argument("-flatten",action="store_true",help="Flatten water (experimental - will require a buffered dem)")
parser.add_argument("-smooth_rad",type=int,help="Specify a positive radius to smooth large (dry) triangles (below houses etc.)",default=0)
parser.add_argument("-tiledb",help="Specify tile db explicitly rather than defining get_neighbours in parameter file")
parser.add_argument("las_file",help="Input las tile (the important bit is tile name).")
parser.add_argument("layer_def_file",help="Input parameter file specifying connections to reference layers. Can be set to 'null' - meaning ref-layers will not be used.")
parser.add_argument("output_dir",help="Where to store the dems e.g. c:\\final_resting_place\\")

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
	
def is_water(dem,water_mask,trig_mask,z_cut):
	#experimental
	print("Finding water...")
	t1=time.clock()
	water_mask=image.morphology.binary_dilation(water_mask,np.ones((7,7)),4,mask=trig_mask)
	M=image.filters.minimum_filter(dem,21)
	N=np.logical_and(water_mask,(dem-M)<z_cut)
	N|=np.logical_and(water_mask,trig_mask)
	N=image.morphology.binary_opening(N)
	t2=time.clock()
	print("Finished water...took: {0:.2f} s".format(t2-t1))
	return N

def expand_water(trig_mask,lake_mask,mincount=100):
	L,nf=image.measurements.label(trig_mask)
	print L.shape, L.dtype, nf, lake_mask.shape,lake_mask.sum(),L.size, lake_mask.dtype
	#LC=np.where(np.bincount(L.flatten())>mincount)[0]
	#find (large) components both in lake_mask and exterior
	IN=np.unique(L[lake_mask])
	OUT=np.unique(L[np.logical_not(lake_mask)])
	INOUT=set(IN).intersection(set(OUT))
	#LINOUT=INOUT.intersection(set(LC)) #largish components both in mask and outside
	for i in INOUT:
		#print i
		if i>0:
			lake_mask|=(L==i)
			#print lake_mask.sum()
	#do some more morphology to lake_mask and dats it
	return lake_mask
	
def gridit(pc,extent,cs,g_warp=None,doround=False):
	if pc.triangulation is None:
		pc.triangulate()
	g,t=pc.get_grid(x1=extent[0],x2=extent[2],y1=extent[1],y2=extent[3],cx=cs,cy=cs,nd_val=ND_VAL,method="return_triangles")
	M=(g.grid!=ND_VAL)
	if not M.any():
		return None,None
	if g_warp is not None:
		g.grid[M]-=g_warp[M]  #warp to dvr90
	g.grid=g.grid.astype(np.float32) 
	t.grid=t.grid.astype(np.float32)
	if doround:
		print("Warning: experimental rounding to mm level")
		g.grid=np.around(g.grid,3)
	return g,t


#default neighbour getter - using a tiledb like tile_coverage.py
def get_neighbours(tilename):
	con=sqlite3.connect(TILE_DB)
	cur=con.cursor()
	cur.execute("select row,col from coverage where tile_name=?",(tilename,))
	data=cur.fetchone()
	row,col=data
	cur.execute("select path from coverage where abs(row-?)<2 and abs(col-?)<2",(row,col))
	data=cur.fetchall()
	ret=[(p,cut_terrain,cut_surface,H_SYS) for p in data]
	return ret
	

NAMES=["MAP_CONNECTION","LAKE_SQL","RIVER_SQL","SEA_SQL","BUILD_SQL","get_neighbours"] #get neighbours is a function which will give neighbours of a given tile...

		
def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	kmname=constants.get_tilename(lasname)
	layer_def_file=pargs.layer_def_file
	if layer_def_file!="null":
		fargs={} #dict for holding reference names
		try:
			execfile(layer_def_file,fargs)
		except Exception,e:
			print("Unable to parse layer definition file "+layer_def_file)
			print(str(e))
	else:
		#nothing defined!
		fargs=dict.fromkeys(NAMES,None)
	if pargs.tiledb is not None:
		global TILE_DB
		fargs["get_neighbours"]=get_neighbours
		TILE_DB=pargs.tile_db #slightly clumsy...
	for name in NAMES:
		if not name in fargs:
			raise ValueError(name+" must be defined in parameter file! (but can be set to None)")
	if fargs["get_neighbours"] is None:
		raise ValueError("-tile_db must be specified or get_neighbours defined in parameter file!")
		
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	print("Using default srs: %s" %(SRS_PROJ4))
	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	extent_buf=extent+(-bufbuf,-bufbuf,bufbuf,bufbuf)
	grid_buf=extent+np.array([-cell_buf,-cell_buf,cell_buf,cell_buf],dtype=np.float64)*gridsize
	assert((extent_buf[:2]<grid_buf[:2]).all()) #just checking...
	assert(modf((extent[2]-extent[0])/gridsize)[0]==0.0)
	terrainname=os.path.join(pargs.output_dir,"dtm_"+kmname+".tif")
	surfacename=os.path.join(pargs.output_dir,"dsm_"+kmname+".tif")
	terrain_exists=os.path.exists(terrainname)
	surface_exists=os.path.exists(surfacename)
	if pargs.dsm:
		do_dsm=pargs.overwrite or  (not surface_exists)
	else:
		do_dsm=False
	if do_dsm:
		do_dtm=True
	else:
		do_dtm=pargs.dtm and (pargs.overwrite or (not terrain_exists))
	if not (do_dtm or do_dsm):
		print("dtm already exists: %s" %terrain_exists)
		print("dsm already exists: %s" %surface_exists)
		print("Nothing to do - exiting...")
		return 2
	#### warn on smoothing #####
	if pargs.smooth_rad>cell_buf:
		print("Warning: smoothing radius is larger than grid buffer")
	tiles=fargs["get_neighbours"](kmname)
	bufpc=None
	geoid=grid.fromGDAL(GEOID_GRID,upcast=True)
	for path,ground_cls,surf_cls,h_system in tiles:
		print("Reading: "+path)
		if os.path.exists(path):
			#check sanity
			assert(set(ground_cls).issubset(set(surf_cls)))
			assert(h_system in ["dvr90","E"])
			pc=pointcloud.fromLAS(path,include_return_number=True).cut_to_box(*extent_buf).cut_to_class(surf_cls) #works as long cut_terrain is a subset of cut_surface...!!!!
			if pc.get_size()>0:
				M=np.zeros((pc.get_size(),),dtype=np.bool)
				#reclass hack
				for c in ground_cls:
					M|=(pc.c==c)
				pc.c[M]=2
				#warping to hsys
				if h_system!=pargs.h_sys and not pargs.nowarp:
					print("Warping!")
					if pargs.h_sys=="E":
						pc.toE()
					else:
						pc.toH()
				if bufpc is None:
					bufpc=pc
				else:
					bufpc.extend(pc)
			del pc
		else:
			print("Neighbour "+path+" does not exist.")
	if bufpc is None:
		return 3
	print("done reading")
	print("Bounds for bufpc: %s" %(str(bufpc.get_bounds())))
	print("# all points: %d" %(bufpc.get_size()))
	if bufpc.get_size()>3:
		rc1=0
		rc2=0
		dtm=None
		dsm=None
		lake_mask=None
		if do_dtm:
			terr_pc=bufpc.cut_to_class(2)
			if terr_pc.get_size()>3:
				print("Doing terrain")
				dtm,trig_grid=gridit(terr_pc,grid_buf,gridsize,None,doround=pargs.round) #TODO: use t to something useful...
				if dtm is not None:
					map_cstr=fargs["MAP_CONNECTION"] 
					if map_cstr is not None: #setting this to None will mean NO tricks...
						lake_mask=np.zeros(dtm.grid.shape,dtype=np.bool)
						print("Rasterising vector layers")
						for key in ["LAKE_SQL","RIVER_SQL","SEA_SQL"]:
							if fargs[key] is not None:
								print("Burning "+fargs[key])
								t1=time.clock()
								lake_mask|=vector_io.burn_vector_layer(map_cstr,dtm.geo_ref,dtm.grid.shape,layersql=fargs[key])
								t2=time.clock()
								print("Took: {0:.2f}s".format(t2-t1))
						build_mask=None
						if fargs["BUILD_SQL"] is not None:
							print("Burning buildings...")
							t1=time.clock()
							build_mask=vector_io.burn_vector_layer(map_cstr,dtm.geo_ref,dtm.grid.shape,layersql=fargs["BUILD_SQL"])
							t2=time.clock()
							print("Took: {0:.2f}s".format(t2-t1))
							
						ds=None
						T=trig_grid.grid>pargs.triangle_limit
						if T.any(): #TODO: move this up...
							print("Expanding water mask")
							t1=time.clock()
							lake_mask=expand_water(T,lake_mask)
							t2=time.clock()
							print("Took: {0:.2f}s".format(t2-t1))
							if build_mask is not None:
								lake_mask&=np.logical_not(build_mask) #xor
							print("Filling in large triangles...")
							M=np.logical_and(T,lake_mask)
							print("Lake cells: %d" %(lake_mask.sum()))
							print("Bad cells: %d" %(M.sum()))
							zlow=array_geometry.tri_filter_low(terr_pc.z,terr_pc.triangulation.vertices,terr_pc.triangulation.ntrig,pargs.zlim)
							if pargs.debug:
								dd=terr_pc.z-zlow
								print dd.mean(),(dd!=0).sum()
							terr_pc.z=zlow
							dtm_low,trig_grid=gridit(terr_pc,grid_buf,gridsize,None,doround=pargs.round)
							dtm.grid[M]=dtm_low.grid[M]
							del dtm_low
							if pargs.flatten:
								print("Smoothing water...") #hmmm - only water??
								t1=time.clock()
								F=array_geometry.masked_mean_filter(dtm.grid,M,4) #TODO: specify as global...
								#M=np.logical_and(M,np.fabs(dtm.grid-F)<0.2)
								dtm.grid[T]=F[T]
								t2=time.clock()
								print("Took: {0:.2f}s".format(t2-t1))
							if pargs.smooth_rad>0:	
								print("Smoothing below houses (probably)...")
								t1=time.clock()
								M=np.logical_and(T,np.logical_not(lake_mask))
								M=image.morphology.binary_dilation(M)
								F=array_geometry.masked_mean_filter(dtm.grid,M,pargs.smooth_rad)
								#M=np.logical_and(M,np.fabs(dtm.grid-F)<0.2)
								dtm.grid[T]=F[T]
								t2=time.clock()
								print("Took: {0:.2f}s".format(t2-t1))
								M=np.logical_and(T,np.logical_not(lake_mask))
								del F
							del trig_grid
							del T
					else:
						print("Reference data not specified.")
					if pargs.dtm and (pargs.overwrite or (not terrain_exists)):
						dtm.shrink(cell_buf).save(terrainname, dco=["TILED=YES","COMPRESS=DEFLATE","PREDICTOR=3","ZLEVEL=9"],srs=SRS_WKT)
					rc1=0
				else:
					rc1=3
			else:
				rc1=3
			del terr_pc
		if do_dsm:
			surf_pc=bufpc.cut_to_return_number(1)
			del bufpc
			if surf_pc.get_size()>3:
				print("Doing surface")
				dsm,trig_grid=gridit(surf_pc,grid_buf,gridsize,None,doround=pargs.round)
				if dsm is not None:
					if dtm is not None and lake_mask is not None: 
						#now we are in a position to handle water...
						T=trig_grid.grid>pargs.triangle_limit
						if T.any():
							print("Filling in large triangles...")
							M=np.logical_and(T,lake_mask)
							print("Lake cells: %d" %(lake_mask.sum()))
							print("Bad cells: %d" %(M.sum()))
							dsm.grid[M]=dtm.grid[M]
							if pargs.debug:
								print dsm.grid.shape
								t_name=os.path.join(pargs.output_dir,"triangles_"+kmname+".tif")
								trig_grid.shrink(cell_buf).save(t_name,dco=["TILED=YES","COMPRESS=LZW"])
								w_name=os.path.join(pargs.output_dir,"water_"+kmname+".tif")
								wg=grid.Grid(lake_mask,dsm.geo_ref,0)
								wg.shrink(cell_buf).save(w_name,dco=["TILED=YES","COMPRESS=LZW"])
					else:
						print("Lake tile does not exist... no insertions...")
					dsm.shrink(cell_buf).save(surfacename, dco=["TILED=YES","COMPRESS=DEFLATE","PREDICTOR=3","ZLEVEL=9"],srs=SRS_WKT)
					rc2=0
				else:
					rc2=3
			else:
				rc2=3
			del surf_pc
				
		return max(rc1,rc2)
	else:	
		return 3
	
	

	
	
if __name__=="__main__":
	main(sys.argv)
	
