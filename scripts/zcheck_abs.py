#############################
## zcheck_abs script. Checks ogr point datasources against strips from pointcloud....
#############################
import sys,os,time
import numpy as np
from osgeo import ogr
from thatsDEM import pointcloud,vector_io,array_geometry,report,array_factory
import dhmqc_constants
from utils.names import get_1km_name
#Tolerances for triangles...
#angle tolerance
angle_tolerance=50.0
#xy_tolerance
xy_tolerance=2.0
#z_tolerance
z_tolerance=1.0
#The class(es) we want to look at...
CUT_CLASS=dhmqc_constants.terrain
#The z-interval we want to consider for the input LAS-pointcloud...
Z_MIN=-20
Z_MAX=200
#Default buffer size for cutlines (roads...)
BUF_SIZE=3

def usage():
	print("Call:\n%s <las_file_to_check> <reference_point_datasource> (options)" %os.path.basename(sys.argv[0]))
	print("Input reference geometries can be 3D points or 3D line features.")
	print("Options which specify the format of reference point data (mutually exclusive):")
	print("-text [-delim <delim>]    : Simple text (xyz). -delim <delim> can be used to specify delimiter character(s).") 
	print("-grid                     : Constructs a pointcloud form a (GDAL readable) grid.")
	print("-las [-class <cut_class>] : LAS input. Cut to class <cut_class> if given. Else cropped to 'terrain'.")
	print("-lines                    : OGR readable 3D line features.")
	print("If any of the above is NOT given the input points are assumed to be an OGR-readable source of point features.") 
	print("Other options:")
	print("-use_local                : Use local datasource for reporting.")
	print("-ftype <type>             : Specify the feature type for reporting (e.g 'patch'). Will otherwise be determined by the specified format") 
	print("-toE                      : Warp the points from dvr90 to ellipsoidal heights. (TODO)")
	print("-cutlines <ogr_lines> [-bufsize <buf>]: Cut the input pointdata to buffer(s) along the lines given in <ogr_lines>")
	print("The -cutlines option do NOTHING if input is already in -lines format.")
	sys.exit()


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
	if len(args)<3:
		usage()
	#standard dhmqc idioms....#
	lasname=args[1]
	pointname=args[2]
	kmname=get_1km_name(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	use_local="-use_local" in args
	if use_local:
		print("Using local data source for reporting.")
	else:
		print("Using global data source for reporting.")
	ds_report=report.get_output_datasource(use_local)
	if ds_report is None:
		print("Failed to open report datasource - you might need to CREATE one...")
	pc=pointcloud.fromLAS(lasname).cut_to_z_interval(Z_MIN,Z_MAX).cut_to_class(CUT_CLASS) #what to cut to here...??
	pc_ref=None #base reference pointcloud
	pc_refs=[] #list of possibly 'cropped' pointclouds...
	if "-text" in args:
		delim=None
		if "-delim" in args:
			i=args.index("-delim")
			delim=args[i+1]
		pc_ref=pointcloud.fromText(pointname,delim)
		ftype="patch"
	elif "-las" in args:
		cut_to=CUT_CLASS
		if "-class" in args:
			i=args.index("-class")
			cut_to=int(args[i+1])
		pc_ref=pointcloud.fromLAS(pointname).cut_to_class(cut_to)
		ftype="las"
	elif "-lines" in args:
		geoms=vector_io.get_geometries(pointname)
		#test geometry dimension
		if len(geoms)>0 and geoms[0].GetDimension()>0:
			for geom in geoms:
				xyz=array_geometry.ogrline2array(geom,flatten=False)
				pc_refs.append(pointcloud.Pointcloud(xyz[:,:2],xyz[:,2]))
		ftype="lines"
	elif "-grid" in args:
		pc_ref=pointcloud.fromGrid(pointname)
		ftype="grid"
	else: #default
		pc_ref=pointcloud.fromOGR(pointname)
		ftype="patch"
	if "-ftype" in args:
		i=args.index("-ftype")
		ftype=args[i+1]
	if "-cutlines" in args: #cut to lines
		if len(pc_refs)>0:
			print("-cutlines not meaningfull for line input...")
		else:
			buf_size=BUF_SIZE
			if "-buf" in args:
				i=args.index("-buf")
				buf_size=float(args[i+1])
			print("Cutting reference input points to line buffers with distance %.2f m" %buf_size) 
			i=args.index("-cutlines")
			line_name=args[i+1]
			geoms=vector_io.get_geometries(line_name)
			for geom in geoms:
				line_array=array_geometry.ogrline2array(geom,flatten=True)
				pc_refs.append(pc_ref.cut_to_line_buffer(line_array,buf_size))
	elif len(pc_refs)==0:
		pc_refs=[pc_ref]
	#TODO: warping loop here....	
	print("Checking %d point sets" %len(pc_refs))
	#Prepare center of mass geometries for reporting
	#Loop over strips#
	for id in pc.get_pids():
		print("%s\n" %("+"*70))
		print("Strip id: %d" %id)
		pc_c=pc.cut_to_strip(id)
		if pc_c.get_size()<50:
			print("Not enough points...")
			continue
		might_intersect=[]
		for i,pc_r in enumerate(pc_refs):
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
			pc_r=pc_refs[i].cut_to_box(*(pc_c.get_bounds()))
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
			if ds_report is not None:
				report.report_abs_z_check(ds_report,kmname,m,sd,n,id,ftype,ogr_geom=cm_geom)
		if not any_checked:
			print("Strip did not intersect any point 'patch'...")


if __name__=="__main__":
	main(sys.argv)