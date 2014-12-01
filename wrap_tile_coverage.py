#####################################################
## Write a simple sqlite-file with tile coverage geometries...  (tifs, las, etc..)##
#####################################################
import os, sys, glob
import argparse
import tile_coverage

parser=argparse.ArgumentParser(description="Write sqlite files readable by e.g. ogr with tile coverage from input directories.")
parser.add_argument("dirs",help="Glob pattern matching directories, e.g. <path>/*dtm")
parser.add_argument("files",help="Glob pattern matching files in directories, e.g *.laz, *.las or *.tif")
parser.add_argument("outdir",help="Output directory of sqlite files.")

def main(args):
	pargs=parser.parse_args(args[1:])
	dirs=glob.glob(pargs.dirs)
	isdirs=filter(os.path.isdir,dirs)
	outdir=pargs.outdir
	if len(isdirs)==0:
		print("No directories in "+pargs.dirs)
		return 1
	if not os.path.exists(outdir):
		os.mkdir(outdir)
	for d in isdirs:
		print("Doing "+d)
		pat=os.path.join(d,pargs.files)
		files=glob.glob(pat)
		if len(files)==0:
			print("Nothing matched by "+pargs.files+" in "+d)
			continue
		outname=os.path.join(outdir,os.path.basename(d)+"_coverage.sqlite")
		if os.path.exists(outname):
			try:
				os.remove(outname)
			except:
				print("Failed to delete "+outname)
				continue
		print("Writing "+outname+".....")
		tile_coverage.main(["tile_coverage",pat,outname])
		
	return 0

if __name__=="__main__":
	main(sys.argv)