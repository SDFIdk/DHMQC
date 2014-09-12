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

cut_terrain=[2,9,17]
cut_surface=[2,3,4,5,6,9,17]
bufbuf = 200


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
	kmname=constants.get_tilename(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	print lasfolder
	
	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	
	center_x=(extent[2]+extent[0])*0.5
	center_y=(extent[3]+extent[1])*0.5
	#extent=[E*1000,N*1000,(E+1)*1000,(N+1)*1000]

	#extent_buf=[extent[0]-bufbuf,extent[1]-bufbuf,extent[2]+bufbuf,extent[3]+bufbuf]
	extent_buf=extent+(-bufbuf,-bufbuf,bufbuf,bufbuf)

	
	basisname=os.path.splitext(os.path.basename(lasname))[0]
	
	surfname=os.path.join(pargs.output_dir,basisname+"_surface.tif")
	terrainname=os.path.join(pargs.output_dir,basisname+"_terrain.tif")
	if os.path.exists(surfname):
		print(surfname+" already exists... exiting...")
		return 0
	

	pcA={}
	for j in range(-1, 2):
		for i in range(-1, 2): 
			#aktN=N-j
			#aktE=E+i
			#aktFnam='1km_'+str(aktN)+'_'+str(aktE)+'.las'
			aktFnam=constants.point_to_tilename(center_x+i*constants.tile_size,center_y-j*constants.tile_size)+".las" # array indexing: neg. j is 'up'
			aktFnam=os.path.join(lasfolder,aktFnam)
			print("Offset x:%d,y:%d, reading: %s" %(i,j,aktFnam))
			if os.path.exists(aktFnam):
				#cls cut will work as long as cut_terrain is a subset of cut_surface
				pcA[(i,j)]=pointcloud.fromLAS(aktFnam,include_return_number=True,xy_box=extent_buf, cls=cut_surface)
			else:
				print("Neighbour (%d,%d) does not exist." %(i,j))

	print("done reading")
	if pcA[(0,0)].get_size()<2:
		print("Few points in tile - wont grid...")
		return 0
	#Do terrain first
	bufpc=pcA[(0,0)].cut_to_class(cut_terrain) #will return a new pc object unless it is empty?? Hmmm - consider logic here... - fixed!!!
	for key in pcA:
		if key!=(0,0):
			tc=pcA[key].cut_to_class(cut_terrain)
			print key
			if tc.get_size()>0:
				bufpc.extend(tc)
				print bufpc.get_size()
			
	print bufpc.get_bounds()
	if bufpc.get_size()>3:
		print "triangulating terrain"
		bufpc.triangulate()
		g=bufpc.get_grid(x1=extent[0],x2=extent[2],y1=extent[1],y2=extent[3],cx=gridsize,cy=gridsize)
		g.grid=g.grid.astype(np.float32)
		del bufpc
		g.save(surfname, dco=[])
		#delete grid from memory to save RAM...
		del g
	#Do the surface
	#save RAM
	for key in pcA:
		pcA[key]=pcA[key].cut_to_return_number(1)
	
	bufpc=pcA[(0,0)]
	if bufpc.get_size()>2:
		for key in pcA:
			if key!=(0,0) and pcA[key].get_size()>0:
				bufpc.extend(pcA[key])
				print key
				print bufpc.get_size()
		print bufpc.get_bounds()
		print "triangulating surface"	
		bufpc.triangulate()
		g=bufpc.get_grid(x1=extent[0],x2=extent[2],y1=extent[1],y2=extent[3],cx=gridsize,cy=gridsize)
		del bufpc
		del pcA #free RAM for other processes...
		g.grid=g.grid.astype(np.float32)
		g.save(surfname, dco=[])
	return 0

	
	
if __name__=="__main__":
	main(sys.argv)
	
