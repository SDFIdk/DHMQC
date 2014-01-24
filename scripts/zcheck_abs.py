#############################
## zcheck_abs script. Checks ogr point datasources against strips from pointcloud....
#############################
import sys,os,time
import numpy as np
from thatsDEM import pointcloud,vector_io,array_geometry,report,array_factory
import dhmqc_constants
from utils.names import get_1km_name
from utils.stats import get_dz_stats
#Tolerances for triangles...
#angle tolerance
angle_tolerance=50.0
#xy_tolerance
xy_tolerance=2.0
#z_tolerance
z_tolerance=1.0
#The class(es) we want to look at...
cut_class=[dhmqc_constants.terrain,dhmqc_constants.surface]

def usage():
	print("Call:\n%s <las_file> <ogr_point_file> -use_local" %os.path.basename(sys.argv[0]))
	print("Use -use_local to force use of local database for reporting.")
	sys.exit()


def check_points(pc,xy,z,DEBUG=False):
	z_out=pc.controlled_interpolation(xy,nd_val=-999)
	M=(z_out!=-999)
	z_good=z[M]
	if z_good.size<2:
		return None
	dz=z_out[M]-z_good
	m,sd,l1,n=get_dz_stats(dz)
	return m,sd,n #consider using also l1....


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
	pc=pointcloud.fromLAS(lasname).cut_to_z_interval(-20,200).cut_to_class(cut_class) #what to cut to here...??
	points=vector_io.get_geometries(pointname)
	points_arr=array_geometry.ogrpoints2array(points)
	xy=array_factory.point_factory(points[:,:2])
	z=array_factory.z_factory(points[:,2])
	del points  #not needed anymore...
	bbox=array_geometry.get_bounds(xy)
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
			report.report_abs_z_check(ds_report,kmname,m,sd,n,id,ogr_geom="what??")


if __name__=="__main__":
	main(sys.argv)