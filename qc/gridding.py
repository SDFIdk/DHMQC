import os,sys
from thatsDEM import pointcloud, array_geometry,grid
from thatsDEM import dhmqc_constants as constants
import numpy as np
cs=0.4
TILE_SIZE=1e3

def usage():
	print("Usage:\n%s <las file> <output dir>" %os.path.basename(sys.argv[0]))
	print(" ")
	print("<las file>        The input las file to grid")
	print("<output dir>      Where to put the files")
	sys.exit(1)

# To do... 
# - Only use 1st return (highest point) for each cell. 
# - Import eight surrounding tiles
	
def main(args):
	if len(args)<3:
		usage()
	lasname=args[1]
	outdir=args[2]
	kmname=constants.get_tilename(lasname)
	try:
		N,E=kmname.split("_")[1:]
		N=int(N)
		E=int(E)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	xll=E*1e3
	yll=N*1e3
	xlr=xll+TILE_SIZE
	yul=yll+TILE_SIZE
	o_name_grid=kmname+"_terrain"
	o_name_surface=kmname+"_surface"
	pc=pointcloud.fromLAS(lasname,include_return_number=True)
	pc_=pc.cut_to_class([constants.terrain,constants.water])
	pc_.triangulate()
	print("Gridding...")
	g=pc_.get_grid(x1=xll,x2=xlr,y1=yll,y2=yul,cx=cs,cy=cs)
	g.grid=g.grid.astype(np.float32)
	g.save(os.path.join(outdir,o_name_grid+".tif"))
	print("Hillshading...")
	h=g.get_hillshade()
	h.save(os.path.join(outdir,o_name_grid+"_shade_"+".tif"))
	print("Gridding...")
	del h
	del g
	pc_=pc.cut_to_return_number(1).cut_to_class([constants.terrain,constants.low_veg,constants.med_veg,constants.high_veg,constants.building,constants.water,constants.bridge])
	pc_.triangulate()
	g=pc_.get_grid(x1=xll,x2=xlr,y1=yll,y2=yul,cx=cs,cy=cs)
	g.grid=g.grid.astype(np.float32)
	g.save(os.path.join(outdir,o_name_surface+".tif"))
	print("Hillshading...")
	h=g.get_hillshade()
	h.save(os.path.join(outdir,o_name_surface+"_shade_"+".tif"))
	return 0


if __name__=="__main__":
	sys.exit(main(sys.argv))