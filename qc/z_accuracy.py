from __future__ import print_function
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
#############################
## zcheck_abs script. Checks ogr point datasources against strips from pointcloud....
#############################
from builtins import str
from builtins import range
import sys,os,time
import numpy as np
from osgeo import ogr
from qc.thatsDEM import pointcloud,vector_io,array_geometry,array_factory,grid
from qc.db import report
from . import dhmqc_constants as constants
from qc.utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
#path to geoid
GEOID_GRID=os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b.utm32")
#Tolerances for triangles...
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
#Default buffer size for cutlines (roads...)
BUF_SIZE=3
#TODO: migrate to new argparse setup
progname=os.path.basename(__file__).replace(".pyc",".py")
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Check accuracy relative to reference data pr. strip.",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
parser.add_argument("-class",dest="cut_to",type=int,default=CUT_CLASS,help="Specify ground class for input las file (will use default defined in constants).")

parser.add_argument("-toE",action="store_true",help=" Warp the points from dvr90 to ellipsoidal heights.")
parser.add_argument("-ftype",help="Specify feature type name for reporting (will otherwise be determined from reference data type)")
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database)",type=str)
group2=parser.add_mutually_exclusive_group(required=True)
group2.add_argument("-lines",action="store_true",help="Specify reference data as OGR readable 3D line features.")
group2.add_argument("-multipoints",action="store_true",help="Specify reference data as OGR readable 3D multipoint features.")

parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("ref_data",help="Reference data (path, connection string etc).")

def usage():
	parser.print_help()

def check_points(pc,pc_ref):
	z_out=pc.controlled_interpolation(pc_ref.xy,nd_val=-999)
	M=(z_out!=-999)
	z_good=pc_ref.z[M]
	if z_good.size<1:
		return None
	dz=z_out[M]-z_good
	#we do not remove outliers here...
	m=dz.mean()
	sd=np.std(dz)
	n=dz.size
	print("DZ-stats: (outliers NOT removed)")
	print("Mean:               %.2f m" %m)
	print("Standard deviation: %.2f m" %sd)
	print("N-points:           %d" %n)
	return m,sd,n #consider using also l1....


def do_it(xy,z,km_name="",ftype="NA",ds_report=None):
	bbox=array_geometry.get_bounds(xy)
	bbox_poly=array_geometry.bbox_to_polygon(bbox) #perhaps use that for intersection to speed up??
	#calulate center of mass for reporting...
	cm_x,cm_y=xy.mean(axis=0)
	cm_z=z.mean()
	print("Center of mass: %.2f %.2f %.2f" %(cm_x,cm_y,cm_z))
	cm_geom=ogr.Geometry(ogr.wkbPoint25D)
	cm_geom.SetPoint(0,cm_x,cm_y,cm_z)
	for id in pc.get_pids():
		print("%s\n" %("+"*70))
		print("Strip id: %d" %id)
		pc_=pc.cut_to_strip(id)
		if pc_.get_size()<50:
			print("Not enough points...")
			continue
		if not pc_.might_intersect_box(bbox):
			print("Point patch does not intersect strip...")
			continue
		pc_.triangulate()
		pc_.calculate_validity_mask(angle_tolerance,xy_tolerance,z_tolerance)
		print("Stats for check against strip %d:" %id)
		stats=check_points(pc_,xy,z)
		if stats is None:
			print("Not enough points in proper triangles...")
			continue
		m,sd,n=stats
		#what geometry should be reported, bounding box??
		if ds_report is not None:
			report.report_abs_z_check(ds_report,kmname,m,sd,n,id,ftype,ogr_geom=cm_geom)

def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception as e:
		print(str(e))
		return 1
	kmname=constants.get_tilename(pargs.las_file)
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	lasname=pargs.las_file
	pointname=pargs.ref_data
	use_local=pargs.use_local
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportZcheckAbs(use_local)

	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception as e:
		print("Could not get extent from tilename.")
		extent=None
	pc_ref=None #base reference pointcloud
	pc_refs=[] #list of possibly 'cropped' pointclouds...
	if pargs.multipoints:
		ftype="multipoints"
		explode=False
	elif pargs.lines:
		ftype="lines"
		explode=True
	geoms=vector_io.get_geometries(pointname,pargs.layername,pargs.layersql,extent,explode=explode)
	for geom in geoms:
		xyz=array_geometry.ogrgeom2array(geom,flatten=False)
		if xyz.shape[0]>0:
			pc_refs.append(pointcloud.Pointcloud(xyz[:,:2],xyz[:,2]))
	print("Found %d non-empty geometries" %len(pc_refs))
	if len(pc_refs)==0:
		print("No input geometries in intersection...")
	if pargs.ftype is not None:
		ftype=pargs.ftype
	cut_input_to=pargs.cut_to
	print("Cutting input pointcloud to class %d" %cut_input_to)
	pc=pointcloud.fromAny(lasname).cut_to_class(cut_input_to) #what to cut to here...??
	#warping loop here....
	if (pargs.toE):
		geoid=grid.fromGDAL(GEOID_GRID,upcast=True)
		print("Using geoid from %s to warp to ellipsoidal heights." %GEOID_GRID)
		for i in range(len(pc_refs)):
			toE=geoid.interpolate(pc_refs[i].xy)
			M=(toE==geoid.nd_val)
			if (M.any()):
				print("Warping to ellipsoidal heights produced no-data values!")
				M=np.logical_not(M)
				toE=toE[M]
				pc_refs[i]=pc_refs[i].cut(M)
			pc_refs[i].z+=toE
	#Remove empty pointsets
	not_empty=[]
	for pc_r in pc_refs:
		if pc_r.get_size()>0:
			not_empty.append(pc_r) #dont worry, just a pointer...
		else:
			raise Warning("Empty input set...")
	print("Checking %d point sets" %len(not_empty))
	#Loop over strips#

	for id in pc.get_pids():
		print("%s\n" %("+"*70))
		print("Strip id: %d" %id)
		pc_c=pc.cut_to_strip(id)
		if pc_c.get_size()<50:
			print("Not enough points...")
			continue
		might_intersect=[]
		for i,pc_r in enumerate(not_empty):
			if pc_c.might_overlap(pc_r):
				might_intersect.append(i)
		if len(might_intersect)==0:
			print("Strip does not intersect any point 'patch'...")
			continue
		pc_c.triangulate()
		pc_c.calculate_validity_mask(angle_tolerance,xy_tolerance,z_tolerance)
		#now loop over the patches which might intersect this strip...
		any_checked=False
		for i in might_intersect:
			pc_r=not_empty[i].cut_to_box(*(pc_c.get_bounds()))
			if pc_r.get_size==0:
				continue
			any_checked=True
			print("Stats for check of 'patch/set' %d against strip %d:" %(i,id))
			stats=check_points(pc_c,pc_r)
			if stats is None:
				print("Not enough points in proper triangles...")
				continue
			m,sd,n=stats
			cm_x,cm_y=pc_r.xy.mean(axis=0)
			cm_z=pc_r.z.mean()
			print("Center of mass: %.2f %.2f %.2f" %(cm_x,cm_y,cm_z))
			cm_geom=ogr.Geometry(ogr.wkbPoint25D)
			cm_geom.SetPoint(0,cm_x,cm_y,cm_z)
			#what geometry should be reported, bounding box??
			reporter.report(kmname,id,ftype,m,sd,n,ogr_geom=cm_geom)
		if not any_checked:
			print("Strip did not intersect any point 'patch'...")


if __name__=="__main__":
	main(sys.argv)
