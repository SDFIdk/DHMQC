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
cut_class=[dhmqc_constants.terrain,dhmqc_constants.surface]

def usage():
	print("Call:\n%s <las_file> <point_datasource> [-text] [-delim <delim>] [-use_local] [-ftype <type>]" %os.path.basename(sys.argv[0]))
	print("If -text is NOT specified, it is assumed that the datasource is an OGR readable point data source.")
	print("If -text IS specified, -delim <delim> can be used to specify delimiter character(s).")
	print("Use -use_local to force use of local database for reporting.")
	print("Use -ftype <type> to specify a 'feature' type of points source (patch, road etc.)")
	sys.exit()


def check_points(pc,xy,z,DEBUG=False):
	z_out=pc.controlled_interpolation(xy,nd_val=-999)
	M=(z_out!=-999)
	z_good=z[M]
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
	if "-text" in args:
		delim=None
		if "-delim" in args:
			i=args.index("-delim")
			delim=args[i+1]
		points_arr=np.loadtxt(pointname,delimiter=delim)
	else:
		points=vector_io.get_geometries(pointname)
		points_arr=array_geometry.ogrpoints2array(points)
		del points  #not needed anymore...
	if points_arr.ndim==1:
		points_arr=points_arr.reshape((1,2))
	if "-ftype" in args:
		i=args.index("-ftype")
		ftype=args[i+1]
	else:
		ftype=None
	xy=array_factory.point_factory(points_arr[:,:2])
	z=array_factory.z_factory(points_arr[:,2])
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


if __name__=="__main__":
	main(sys.argv)