import sys,os,time
import  thatsDEM.dhmqc_constants as constants
from argparse import ArgumentParser
import math
import glob
import numpy as np
from subprocess import call
from thatsDEM import pointcloud


#Call from qc_warp with this command line: "python qc_wrap.py dem_gen d:\temp\slet\raa\*.las -targs "D://temp//slet//output" "

#gridsize of the hillshade (always 0.4 m)
gridsize = 0.4

cut_terrain=[2,9]
cut_surface=[2,3,4,5,6,9,17]

progname=os.path.basename(__file__)
parser=ArgumentParser(description="Generate DSM and DTM for a las file. Will try to read surrounding tiles for buffer.",prog=progname)
parser.add_argument("las_file",help="Directory of las files e.g. c:\\mydir\\*.las")
parser.add_argument("output_dir",help="Where to store the hillshade e.g. c:\\final_resting_place\\")

def usage():
	parser.print_help()
		
def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	lasfolder = os.path.dirname(lasname)
	print lasfolder
	kmname=constants.get_tilename(lasname)
	try:
		N,E=kmname.split("_")[1:]
		N=int(N)
		E=int(E)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		ds_lake=None
		return 1
	print N, E
	
	extent=[E*1000,N*1000,(E+1)*1000,(N+1)*1000]
	bufbuf = 200
	extent_buf=[extent[0]-bufbuf,extent[1]-bufbuf,extent[2]+bufbuf,extent[3]+bufbuf]
#	print extent_buf
	
#	print extent
	
	basisname=os.path.splitext(os.path.basename(lasname))[0]
	
	
	if os.path.exists(os.path.join(pargs.output_dir,basisname+"_surface.tif")):
		return
	
#	print dtmname, dsmname
	pcA={}
#	pcA[(0,0)]=pointcloud.fromLAS(lasname)
	for j in range(-1, 2):
		for i in range(-1, 2): 
			aktN=N-j
			aktE=E+i
			aktFnam='1km_'+str(aktN)+'_'+str(aktE)+'.las'
			aktFnam=os.path.join(lasfolder,aktFnam)
			print aktFnam
			if os.path.exists(aktFnam):
				pcA[(i,j)]=pointcloud.fromLAS(aktFnam,True).cut_to_box(extent_buf[0],extent_buf[1],extent_buf[2],extent_buf[3])
#				print pcA[(i,j)].get_bounds()
#				print pcA[(i,j)].get_size()
	print "done reading"

	#Do terrain first
	bufpc=pcA[(0,0)].cut_to_class(cut_terrain)
	for j in range(-1, 2):
		for i in range(-1, 2):
			if ((i!=0) and (j!=0)):
				if (i,j) in pcA:
					tc=pcA[(i,j)].cut_to_class(cut_terrain)
					if tc.get_size()>0:
						bufpc.extend(tc)
					else:
						print i,j
	print bufpc.get_bounds()				
	print "triangulating terrain"
	bufpc.triangulate()
	g=bufpc.get_grid(x1=extent[0],x2=extent[2],y1=extent[1],y2=extent[3],cx=gridsize,cy=gridsize)
	g.grid=g.grid.astype(np.float32)
	g.save(os.path.join(pargs.output_dir,basisname+"_terrain.tif"))
	
	#Do the surface
	bufpc=pcA[(0,0)].cut_to_class(cut_surface).cut_to_return_number(1)
	print bufpc.get_size()
#	print "hertil"
	for j in range(-1, 2):
		for i in range(-1, 2):
			if ((i!=0) and (j!=0)):
				if (i,j) in pcA:
					tc=pcA[(i,j)].cut_to_class(cut_surface).cut_to_return_number(1)
					if tc.get_size()>0:
						bufpc.extend(tc)
					else:
						print i,j
	print bufpc.get_bounds()	
	print "triangulating surface"	
	bufpc.triangulate()
	g=bufpc.get_grid(x1=extent[0],x2=extent[2],y1=extent[1],y2=extent[3],cx=gridsize,cy=gridsize)
	g.grid=g.grid.astype(np.float32)
	g.save(os.path.join(pargs.output_dir,basisname+"_surface.tif"))
	
#	sys.exit(1)
	
	
if __name__=="__main__":
	main(sys.argv)
	
