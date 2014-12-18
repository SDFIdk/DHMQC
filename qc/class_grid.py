import os,sys
from thatsDEM import pointcloud, array_geometry,grid
from thatsDEM import dhmqc_constants as constants
import numpy as np
cs=1
TILE_SIZE=1e3

def usage():
	print("Usage:\n%s <las file> <output dir> -thin" %os.path.basename(sys.argv[0]))
	print(" ")
	print("<las file>        The input las file to grid")
	print("<output dir>      Where to put the files")
	print("Use -thin to apply thinning of pc first!")
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
		xll,yll,xlr,yul=constants.tilename_to_extent(kmname)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	o_name_grid=kmname+"_class"
	pc=pointcloud.fromLAS(lasname) #terrain subset of surf so read filtered...
	print("Gridding classes...")
	g=pc.get_grid(x1=xll,x2=xlr,y1=yll,y2=yul,cx=cs,cy=cs,method="class")
	g.save(os.path.join(outdir,o_name_grid+".tif"),dco=["TILED=YES","COMPRESS=LZW"])
	return 0


if __name__=="__main__":
	sys.exit(main(sys.argv))