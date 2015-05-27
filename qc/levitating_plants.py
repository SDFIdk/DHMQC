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
#####################################
## Voxel Stuff
## Can be used to a lot, really a lot!
## Primarily we want to find points which lie in a vegetation class, but should NOT be included in a DSM
## E.g. points on wires - in general points which are floating in the air without much around them
## But we can also easily find wrongly classified vegetation points on roofs, walls etc...
## In order to find wires with sufficiently dense point distribution to be actually connected to the ground component, we need to do some morphology
## This is still experimental!!
## simlk, oct. 2014
###############################################
import sys,os,time
#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry
from db import report
import numpy as np
import dhmqc_constants as constants
import scipy.ndimage as im
cut_ground=[constants.water,constants.terrain,constants.bridge] #hmmm - can stuff below bridges be floating - no, guess not.
floating_class=[constants.low_veg,constants.med_veg,constants.high_veg]
extended_ground=cut_ground+floating_class #this is what we should find connected components in
surf_without_veg=cut_ground+[constants.building]
HOR=np.zeros((3,3,3),dtype=np.uint8)
HOR[:,:,1]=1

from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
z_min=3  #height above "ground" component in order to be interesting...
adddsm=1.5 #add something to dsm to avoid some floating trees...
max_cor=6
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")
#TODO: add cellsize arg...
#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Voxelise a point cloud and find floating vegetation class components.",prog=progname)

#add some arguments below
parser.add_argument("-voxelh",type=float,default=z_min,help="Specify the minial (voxel) height of a floating voxel. Default: {0:d}".format(z_min))
parser.add_argument("-maxcor", type=int,default=max_cor,help="Specify maximal correlation of an interesting voxel using a 3x3x3 structure element. Default: {0:d}".format(max_cor))
parser.add_argument("-savedsm",action="store_true",help="Save ground+building dsm for debugging.")
parser.add_argument("-adddsm",type=float,default=adddsm,help="Add this amount to generated dsm in order to exclude som floating trees. Default: {0:.2f}".format(adddsm))
parser.add_argument("las_file",help="input las tile.")
parser.add_argument("outdir",help="output directory of csv-file")



def points_in_voxels(pc,mask,x1,y2,z1):
	xyz=((np.column_stack((pc.xy,pc.z))-(x1,y2,z1))*(1,-1,1)).astype(np.int32)
	M=((xyz<(mask.shape[1],mask.shape[0],mask.shape[2])).all(axis=1))
	M&=((xyz>=0).all(axis=1))
	print("%d points inside 3d-array." %(M.sum()))
	xyz=xyz[M]
	N=mask[xyz[:,1],xyz[:,0],xyz[:,2]]
	K=M.copy()
	K[M]=N
	return K
	


def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception,e:
		print(str(e))
		return 1
	kmname=constants.get_tilename(pargs.las_file)
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	lasname=pargs.las_file
	outdir=pargs.outdir
	voxel_h=pargs.voxelh
	maxcor=pargs.maxcor
	adddsm=pargs.adddsm
	if not os.path.exists(outdir):
		os.mkdir(outdir)
	#exclude buildings - if we trust those - to easier find points floating in the air.
	#problem - there will be more vegetation floating around then - some real and some wrongly classified (noisy stuff on roofs etc).
	pc=pointcloud.fromLAS(lasname)
	#gr=pc.cut_to_class(cut_ground)  #not connected to that, and above
	gr_build=pc.cut_to_class(surf_without_veg) #also above that
	voxelise=pc.cut_to_class(extended_ground)
	del pc
	try:
		x1,y1,x2,y2=constants.tilename_to_extent(kmname)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	
	z1,z2=gr_build.get_z_bounds() #include room for everything!!!
	for pc in [voxelise]:
		zz1,zz2=pc.get_z_bounds()
		z1=min(z1,zz1)
		z2=max(z2,zz2)
	print("Z-bounds: %.2f %.2f" %(z1,z2))
	#now construct ground grid
	print("Finding ground (with buildings)...")
	gr_build.triangulate()
	g=gr_build.get_grid(x1=x1,x2=x2,y1=y1,y2=y2,cx=1,cy=1)
	g.grid=g.grid.astype(np.float32)
	print("DSM-bounds (ground+buildings): %d %d" %(g.grid.min(),g.grid.max()))
	print("Max filtering height model slightly to fill holes...")
	g.grid=im.filters.maximum_filter(g.grid,footprint=np.ones((5,5)))
	if pargs.savedsm:
		outname=os.path.join(outdir,kmname+"_dsm.tif")
		g.save(outname,dco=["COMPRESS=LZW"])
	print("Adding %.2f m to dsm..." %adddsm)
	g.grid+=adddsm
	z_build=(g.grid-z1).astype(np.uint32)
	nrows,ncols=g.grid.shape
	nstacks=int(z2-z1)+1
	out=np.zeros((nrows,ncols,nstacks),dtype=np.uint8)
	
	
	del gr_build
	#voxelise proper pc
	print("Voxelising points from ground and veg: %d" %(voxelise.get_size()))
	xyz=((np.column_stack((voxelise.xy,voxelise.z))-(x1,y2,z1))*(1,-1,1)).astype(np.int32)
	assert((xyz>=0).all())
	M=((xyz<(ncols,nrows,nstacks)).all(axis=1))
	M&=((xyz>=0).all(axis=1))
	N=np.logical_not(M)
	no=N.sum()
	print("#points outside voxel-grid: %d" %(no))
	if no>0:
		print xyz[N][:10]
	xyz=xyz[M]
	del M
	del N
	#voxelise it!
	out[xyz[:,1],xyz[:,0],xyz[:,2]]=1
	
	#fill up below ground level
	array_geometry.lib.fill_it_up(out,z_build,nrows,ncols,nstacks)
	#fill the lowest level, if there are holes in dsm
	out[:,:,0]=1
	#find connected components
	labels,nf=im.measurements.label(out,np.ones((3,3,3)))
	print("Number of components: %d" %nf)
	at_ground=np.unique(labels[:,:,0])
	if at_ground.size>1:
		raise Warning("Multiple components at lowest level - needs further investigation!")
		print(str(at_ground))
	gcomp=at_ground.max()
	print("Ground must be: %d" %gcomp)
	M=(labels==gcomp)
	#ok so now check each voxel in compiled code
	#floating in air, above ground component - not really close to building (along walls or on top of roof) -and has 'simple' geometry
	#hmmm - should be above g-component WITH buildings and surface also??
	#now fill up below ground + build + delta
	
	#find stuff thats not connected to ground and is above ground component
	F=np.zeros(labels.shape,dtype=np.int32)
	array_geometry.lib.find_floating_voxels(labels,F,gcomp,labels.shape[0],labels.shape[1],labels.shape[2])
	#np.save(outname,F)
	print("Number of floating voxels ABOVE g-component: %d" %((F>0).sum()))
	F=(F>voxel_h)
	print("Number of floating voxels %d ABOVE g-component: %d" %(voxel_h,F.sum()))
	C=im.filters.correlate(F,np.ones((3,3,3)))
	print("Max. correlation with a ones element set to: %d" %maxcor)
	F=np.logical_and(F,C<maxcor)
	print("Number of floating voxels after filtering: %d" %(F.sum()))
	print("Getting vegetation points inside voxels...")
	veg=voxelise.cut_to_class(floating_class)
	M=points_in_voxels(veg,F,x1,y2,z1)
	print("#All vegetation points: %d" %veg.get_size())
	veg=veg.cut(M)
	print("#Veg. points in voxel mask: %d"%veg.get_size())
	outname=os.path.join(outdir,kmname+"_floating.csv")
	print("Saving "+outname+"...")
	f=open(outname,"w")
	veg.dump_csv(f)
	f.close()
	#dump binary also
	outname=os.path.join(outdir,kmname+"_floating.bin")
	print("Dumping binary to "+outname)
	veg.dump_bin(outname)
	
	
	
	
	
	


if __name__=="__main__":
	main(sys.argv)