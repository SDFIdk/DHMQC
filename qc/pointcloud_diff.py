import sys,os,time
import numpy as np
from osgeo import ogr
from thatsDEM import pointcloud,vector_io,array_geometry,report,array_factory,grid
import thatsDEM.dhmqc_constants as constants
from utils.names import get_1km_name
#path to geoid 
GEOID_GRID=os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b.utm32")
#angle tolerance
angle_tolerance=50.0
#xy_tolerance
xy_tolerance=2.0
#z_tolerance
z_tolerance=1.0
#The class(es) we want to look at...
CUT_CLASS=constants.terrain
#The z-interval we want to consider for the input LAS-pointcloud...
Z_MIN=-20
Z_MAX=200
CELL_SIZE=100  #100 m cellsize in density grid
TILE_SIZE=1000
ND_VAL=-9999
MIN_POINT_LIMIT=2  #at least this number of reference points in order to grid...
MIN_POINT_LIMIT_BASE=5 # at least this many point in input las to bother
GRIDS_OUT="diff_grids"  #due to the fact that this is being called from qc_wrap it is easiest to have a standard folder for output..


def usage():
	print("To run:")
	print("%s <las_tile> <las_ref_tile> (options)" %(os.path.basename(sys.argv[0])))
	print("Options:")
	print("-cs <cell_size> to specify cell size of grid. Default 100 m (TILE_SIZE must be divisible by cs)")
	print("-class <class> to specify ground class of reference las tile.")
	print("-toE to warp reference points to ellipsoidal heights.")
	sys.exit()


def check_points(pc,pc_ref):
	z_out=pc.controlled_interpolation(pc_ref.xy,nd_val=-999)
	M=(z_out!=-999)
	z_good=pc_ref.z[M]
	if z_good.size<1:
		return None
	dz=z_out[M]-z_good
	xy=pc_ref.xy[M]
	pc_=pointcloud.Pointcloud(xy,dz)
	m=dz.mean()
	sd=np.std(dz)
	n=dz.size
	print("+"*60)
	print("DZ-stats (input/new - reference . Outliers NOT removed):")
	print("Mean:               %.2f m" %m)
	print("Standard deviation: %.2f m" %sd)
	print("N-points:           %d" %n)
	return pc_

#simple gridding 
#method designed to calc. some algebraic quantity within every single cell
def make_grid(xy,z,ncols, nrows, georef, nd_val=-9999, method=np.mean): #gdal-style georef
	out=np.ones((nrows,ncols),dtype=np.float32)*nd_val
	arr_coords=((xy-(georef[0],georef[3]))/(georef[1],georef[5])).astype(np.int32)
	M=np.logical_and(arr_coords[:,0]>=0, arr_coords[:,0]<ncols)
	M&=np.logical_and(arr_coords[:,1]>=0,arr_coords[:,1]<nrows)
	arr_coords=arr_coords[M]
	z=z[M]
	#create flattened index
	B=arr_coords[:,1]*ncols+arr_coords[:,0]
	#now sort array
	I=np.argsort(B)
	arr_coords=arr_coords[I]
	z=z[I]
	#and finally loop through pts just one more time...
	box_index=arr_coords[0,1]*ncols+arr_coords[0,0]
	i0=0
	row=arr_coords[0,1]
	col=arr_coords[0,0]
	for i in xrange(arr_coords.shape[0]):
		b=arr_coords[i,1]*ncols+arr_coords[i,0]
		if (b>box_index):
			#set the current cell
			out[row,col]=method(z[i0:i])
			#set data for the next cell
			i0=i
			box_index=b
			row=arr_coords[i,1]
			col=arr_coords[i,0]
	#set the final cell - corresponding to largest box_index
	assert ((arr_coords[i0]==arr_coords[-1]).all())
	final_val=method(z[i0:])
	out[row,col]=final_val
	return out
			
		
	
	


def main(args):
	if len(args)<3:
		usage()
	#standard dhmqc idioms....#
	lasname=args[1]
	pointname=args[2]
	kmname=get_1km_name(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	if not os.path.exists(GRIDS_OUT):
		os.mkdir(GRIDS_OUT)
	pc=pointcloud.fromLAS(lasname).cut_to_z_interval(Z_MIN,Z_MAX).cut_to_class(CUT_CLASS) #what to cut to here...??
	if pc.get_size()<MIN_POINT_LIMIT_BASE:
		print("Few points, %d, in input pointcloud , won't bother..." %pc.get_size())
		return
	cut_to=CUT_CLASS
	if "-class" in args:
		i=args.index("-class")
		cut_to=int(args[i+1])
	if "-cs" in args:
		try:
			cs=float(args[args.index("-cs")+1])
		except Exception,e:
			print(str(e))
			usage()
	else:
		cs=CELL_SIZE #default
	print("Using cell size: %.2f" %cs)
	pc_ref=pointcloud.fromLAS(pointname).cut_to_class(cut_to)
	print("%d points in reference pointcloud." %pc_ref.get_size())
	if pc_ref.get_size()<MIN_POINT_LIMIT:
		print("Too few, %d, reference points - sorry..." %pc_ref.get_size())
		return
	if ("-toE" in args):
		geoid=grid.fromGDAL(GEOID_GRID,upcast=True)
		print("Using geoid from %s to warp to ellipsoidal heights." %GEOID_GRID)
		toE=geoid.interpolate(pc_ref.xy)
		M=(toE==geoid.nd_val)
		if M.any():
			raise Warning("Warping to ellipsoidal heights produced no-data values!")
			toE=toE[M]
			pc_ref=pc_ref.cut(M)
		pc_ref.z+=toE
	pc.triangulate()
	pc.calculate_validity_mask(angle_tolerance,xy_tolerance,z_tolerance)
	pc_out=check_points(pc,pc_ref)
	ncols_f=TILE_SIZE/cs
	ncols=int(ncols_f)
	nrows=ncols  #tiles are square (for now)
	if ncols!=ncols_f:
		print("TILE_SIZE: %d must be divisible by cell size..." %(TILE_SIZE))
		usage()
	
	try:
		N,E=kmname.split("_")[1:]
		N=int(N)
		E=int(E)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		ds_lake=None
		return 1
	xll=E*1e3
	yll=N*1e3
	xul=xll
	yul=yll+TILE_SIZE
	geo_ref=[xul,cs,0,yul,0,-cs]
	t1=time.clock()
	arr=make_grid(pc_out.xy,pc_out.z,ncols,nrows,geo_ref,ND_VAL,np.mean)
	t2=time.clock()
	print("gridding time: %.3f s" %(t2-t1))
	g=grid.Grid(arr,geo_ref,ND_VAL)
	outname_base="diff_{0:.0f}_".format(cs)+os.path.splitext(os.path.basename(lasname))[0]+".tif"
	outname=os.path.join(GRIDS_OUT,outname_base)
	g.save(outname)
	
if __name__=="__main__":
	main(sys.argv)
			
			
	
	