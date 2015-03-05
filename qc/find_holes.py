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
##  TEMPLATE FOR A TEST TO BE WRAPPED 
##  FILL IN AND DELETE BELOW...
######################################################################################
import sys,os,time
#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry, report, grid
import numpy as np
import scipy.ndimage as image
import  thatsDEM.dhmqc_constants as constants
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
from dem_gen_new import resample_geoid,gridit
TILE_SIZE=constants.tile_size #should be 1km tiles...
cut_to=[constants.terrain,constants.water,constants.bridge]
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Write something here",prog=progname)

#add some arguments below

parser.add_argument("-class",type=int,default=cut_to,help="Specify ground class in reference pointcloud")
parser.add_argument("-cs",type=float,default=1,help="Specify grid ")
parser.add_argument("-outdir",default="hole_grids",help="Output dir for grids")
parser.add_argument("-alot",action="store_true",help="do a lot of stuff")
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")

parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("ref_data",help="input reference data connection string (e.g to a db, or just a path to a shapefile).")
parser.add_argument("param_file",help="Parameter file with db-connections to rasterise reference vector layers.")

#PARAMETER FILE MUST DEFINE
#MAP_CONNECTION
#LAYERSQL_FOREST
#LAYERSQL_LAKES
#LAYERSQL_RIVERS
#LAYERSQL_BUILDINGS
NAMES=["MAP_CONNECTION","LAYERSQL_FOREST","LAYERSQL_LAKES","LAYERSQL_BUILDINGS"]
#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
def usage():
	parser.print_help()


	

def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception,e:
		print(str(e))
		return 1
	kmname=constants.get_tilename(pargs.las_file)
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	
	try:
		extent=constants.tilename_to_extent(kmname)
	except Exception,e:
		print("Bad tilename:")
		print(str(e))
		return 1
	fargs={}
	try:
		execfile(pargs.param_file,fargs)
	except Exception,e:
		print("Failed to parse parameter file:\n"+str(e))
		return 1
	for name in NAMES: #test for defined names
		assert(name in fargs)
	cs=pargs.cs
	ncols_f=TILE_SIZE/cs
	ncols=int(ncols_f)
	nrows=ncols  #tiles are square (for now)
	if ncols!=ncols_f:
		print("TILE_SIZE: %d must be divisible by cell size..." %(TILE_SIZE))
		usage()
		return 1
	
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportHoles(pargs.use_local)
	pc=pointcloud.fromLAS(pargs.las_file,include_return_number=True).cut_to_return_number(1) #should be as a terrain grid - but problems with high veg on fields!!!
	pc_ref=pointcloud.fromLAS(pargs.ref_data).cut_to_class(5)
	
	print("points in input-cloud: %d" %pc.get_size())
	#pc.triangulate()
	print("points in ref-cloud: %d" %pc_ref.get_size())
	#pc_ref.triangulate()
	#g_new,t_new=gridit(pc,extent,cs,None)
	#g_old,t_old=gridit(pc_ref,extent,cs,None)
	#Ready for morphology
	#calc vaiance
	#N=image.filters.median_filter(np.sqrt(g_new.dx()**2+g_new.dy()**2),5)
	#M=np.logical_and(g1.grid<1,g2.grid>g1.grid)
	geo_ref=[extent[0],pargs.cs,0,extent[3],0,-pargs.cs]
	print("Sorting...")
	pc.sort_spatially(2*pargs.cs)
	pc_ref.sort_spatially(2*pargs.cs)
	xy=pointcloud.mesh_as_points((nrows,ncols),geo_ref)
	D1=pc.density_filter(pargs.cs,xy).reshape((nrows,ncols))
	D2=pc_ref.density_filter(pargs.cs,xy).reshape((nrows,ncols))
	#DI=pc.distance_filter(pargs.cs,xy).reshape((nrows,ncols))
	print("Filtering...")
	Z1=pc.mean_filter(pargs.cs,xy).reshape((nrows,ncols))
	print Z1.max(),Z1.min()
	Z2=pc_ref.mean_filter(pargs.cs,xy).reshape((nrows,ncols))
	F=pc.var_filter(2*pargs.cs,xy).reshape((nrows,ncols))
	M=(D2>0.5) #we must have old data
	M&=(D1<3) #must not have many new data
	M&=(F<(0.2**2)) #and were flat (or no-data in F)
	M&=np.logical_and(Z1>Z2,Z2>-9999) #and were high
	M|=np.logical_and(Z1==-9999,Z2>-9999) #If we have data in Z2 but nor in Z1
	#M,diff=apply_method(nrows,ncols,pc,pc_ref)
	print("ncells: %d" %M.sum())
	#hmmm - we need to extend M slightly to regions with low density in new and 'high' density in old that intersects this mask!!!
	M2=image.morphology.binary_dilation(M,np.ones((3,3),dtype=np.bool))
	M|=np.logical_and(M2,D2>D1)
	exclude_mask=np.zeros(M.shape,dtype=np.bool)
	for sql in NAMES[1:]:
		print("Burning "+fargs[sql]+"....")
		exclude_mask|=vector_io.burn_vector_layer(fargs["MAP_CONNECTION"],geo_ref,M.shape,layersql=fargs[sql])
	print("Excluded cells: %d" %(exclude_mask.sum()))
	M&=np.logical_not(exclude_mask) #xor
	if pargs.alot:
		if not os.path.exists(pargs.outdir):
			os.mkdir(pargs.outdir)
		pc=pc.cut_to_class([2,9,17])
		print("Making an old grid...")
		cs=0.4
		pc.triangulate()
		outname=os.path.join(pargs.outdir,"old_"+kmname+".tif")
		G=pc.get_grid(x1=extent[0],x2=extent[2],y1=extent[1],y2=extent[3],cx=cs,cy=cs,nd_val=-9999)
		G.save(outname,dco=["TILED=YES","COMPRESS=LZW"])
		pc_cut=pc_ref.cut_to_grid_mask(M,geo_ref)
		print pc_cut.get_size()
		pc_cut.c=np.ones_like(pc_cut.c)*2
		pc.rn=None
		pc.extend(pc_cut)
		print("Making a new grid...")
		pc.triangulate()
		G=pc.get_grid(x1=extent[0],x2=extent[2],y1=extent[1],y2=extent[3],cx=cs,cy=cs,nd_val=-9999)
		G2=pc.get_grid(x1=extent[0],x2=extent[2],y1=extent[1],y2=extent[3],cx=1,cy=1,nd_val=0,method="density")
		outname2=os.path.join(pargs.outdir,"new_"+kmname+".tif")
		G.save(outname2,dco=["TILED=YES","COMPRESS=LZW"])
		outname3=os.path.join(pargs.outdir,"den_new_"+kmname+".tif")
		G2.save(outname3,dco=["TILED=YES","COMPRESS=LZW"])
		outname=os.path.join(pargs.outdir,"holes_"+kmname+".tif")
		holes=grid.Grid(M,geo_ref,0)
		holes.save(outname,dco=["TILED=YES","COMPRESS=LZW"])
	if M.any():
		poly_ds,polys=vector_io.polygonize(M,geo_ref)
		for poly in polys: #yes feature iteration should work...
			g=poly.GetGeometryRef()
			arr=array_geometry.ogrgeom2array(g)
			pc_=pc_ref.cut_to_polygon(arr)
			n=pc_.get_size()
			print n
			if n<2:
				continue
			z1,z2=pc_.get_z_bounds()
			reporter.report(kmname,z1,z2,n,ogr_geom=g)
		polys=None
		poly_ds=None
		
		
	
	

#to be able to call the script 'stand alone'
if __name__=="__main__":
	main(sys.argv)