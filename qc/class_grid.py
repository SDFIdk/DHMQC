import os,sys
from thatsDEM import pointcloud, array_geometry,grid
from thatsDEM import dhmqc_constants as constants
import numpy as np
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
cs=1.0 #default cs

progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Write a grid with cells representing most frequent class.",prog=progname)
parser.add_argument("las_file",help="Input las tile.")
parser.add_argument("output_dir",help="output directory of class grids.")
parser.add_argument("-cs",type=float,help="Cellsize (defaults to {0:.2f})".format(cs),default=cs)

def usage():
	parser.print_help()


def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception,e:
		print(str(e))
		return 1
	lasname=pargs.las_file
	outdir=pargs.output_dir
	kmname=constants.get_tilename(pargs.las_file)
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	try:
		xll,yll,xlr,yul=constants.tilename_to_extent(kmname)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	o_name_grid=kmname+"_class"
	pc=pointcloud.fromLAS(lasname) #terrain subset of surf so read filtered...
	print("Gridding classes...")
	cs=pargs.cs
	g=pc.get_grid(x1=xll,x2=xlr,y1=yll,y2=yul,cx=cs,cy=cs,method="class")
	g.save(os.path.join(outdir,o_name_grid+".tif"),dco=["TILED=YES","COMPRESS=LZW"])
	return 0


if __name__=="__main__":
	sys.exit(main(sys.argv))