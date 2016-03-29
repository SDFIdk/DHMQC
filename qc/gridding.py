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
import os,sys
from thatsDEM import pointcloud, array_geometry,grid
from thatsDEM import dhmqc_constants as constants
import numpy as np
cs=0.4
TILE_SIZE=1e3
cut_surf=[constants.terrain,constants.low_veg,constants.med_veg,constants.high_veg,constants.building,constants.water,constants.bridge]
cut_terrain=[constants.terrain,constants.water]
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
	o_name_grid=kmname+"_terrain"
	o_name_surface=kmname+"_surface"
	if "-thin" in args:
		o_name_grid+="_thin"
		o_name_surface+="_thin"
	pc=pointcloud.fromAny(lasname,include_return_number=True,cls=cut_surf) #terrain subset of surf so read filtered...
	
		
	#First do terrain...
	pc_=pc.cut_to_class(cut_terrain)
	if "-thin" in args:
		print("Thinning...")
		pc_.sort_spatially(2*cs)
		print("Number of points before thinning: %d" %pc_.get_size())
		M=pc_.thinning_filter(cs,den_cut=8,zlim=0.4) #different for surface and terrain
		pc_=pc_.cut(M)
		print("Number of points before after thinning: %d" %pc_.get_size())
	pc_.triangulate()
	print("Gridding...")
	g=pc_.get_grid(x1=xll,x2=xlr,y1=yll,y2=yul,cx=cs,cy=cs)
	g.grid=g.grid.astype(np.float32)
	g.save(os.path.join(outdir,o_name_grid+".tif"))
	print("Hillshading...")
	h=g.get_hillshade()
	h.save(os.path.join(outdir,o_name_grid+"_shade"+".tif"),dco=["TILED=YES","COMPRESS=LZW"])
	print("Gridding...")
	del h
	del g
	pc_=pc.cut_to_return_number(1)
	if "-thin" in args:
		print("Thinning...")
		pc_.sort_spatially(2*cs)
		print("Number of points before thinning: %d" %pc_.get_size())
		M=pc_.thinning_filter(cs,den_cut=10,zlim=0.5) #different for surface and terrain
		pc_=pc_.cut(M)
		print("Number of points before after thinning: %d" %pc_.get_size())
	pc_.triangulate()
	g=pc_.get_grid(x1=xll,x2=xlr,y1=yll,y2=yul,cx=cs,cy=cs)
	g.grid=g.grid.astype(np.float32)
	g.save(os.path.join(outdir,o_name_surface+".tif"))
	print("Hillshading...")
	h=g.get_hillshade()
	h.save(os.path.join(outdir,o_name_surface+"_shade"+".tif"),dco=["TILED=YES","COMPRESS=LZW"])
	return 0


if __name__=="__main__":
	sys.exit(main(sys.argv))
