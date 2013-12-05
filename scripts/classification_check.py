###########################
## beginnings of building classification check
#########################
import sys,os,time
import numpy as np
from thatsDEM import pointcloud,vector_io,array_geometry,report
from utils.names import get_1km_name

DEBUG="-debug" in sys.argv

unclass = 1
groundclass = 2
swathboundaryclass=3
lowpointnoiseclass=7

GOOD_LIMIT=0.90  #at least 90 pct.??

def usage():
	print("Call:\n%s <las_file> <polygon_file> -class <c> -geometry -use_local" %os.path.basename(sys.argv[0]))
	print("Use -class <c> to specify which class to expect inside polygons. Defaults to %d, if not given." %unclass)
	print("Use -geometry to also print geometry for the pointcloud restricted to polygons.")
	print("Use -use_local to force use of local database for reporting.")
	sys.exit()

def main(args):
	lasname=args[1]
	buildname=args[2]
	if len(args)<3:
		usage()
	do_geometry="-geometry" in args
	if "-class" in args:
		c_expcect=int(args[args.index("-class")+1])
	else:
		c_expect=unclass
	kmname=get_1km_name(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	pc=pointcloud.fromLAS(lasname)
	print("Classes in pointcloud: %s" %pc.get_classes())
	polygons=vector_io.get_geometries(buildname)
	nf=0
	use_local="-use_local" in args
	ds_report=report.get_output_datasource(use_local)
	if use_local:
		print("Using local data source for reporting.")
	else:
		print("Using global data source for reporting.")
	if ds_report is None:
		print("Failed to open report datasource - you might need to CREATE one...")
	for polygon in polygons:
		nf+=1
		ml="-"*70
		print("%s\nFeature %d\n%s" %(ml,nf,ml))
		a_polygon=array_geometry.ogrpoly2array(polygon)
		pc_in_poly=pc.cut_to_polygon(a_polygon)
		n_all=pc_in_poly.get_size()
		f_expect=0
		if n_all>0:
			c_all=pc_in_poly.get_classes()
			print("Number of points in polygon:  %d" %n_all)
			print("Classes in polygon:           %s" %(str(c_all)))
			for c in c_all:
				pcc=pc_in_poly.cut_to_class(c)
				n_c=pcc.get_size()
				f_c=n_c/float(n_all)
				print("Class %d::" %c)
				print("   #Points:  %d" %n_c)
				print("   Fraction: %.3f" % f_c)
				if do_geometry and pcc.get_size()>2:
					z1,z2=pcc.get_z_bounds()
					pcc.triangulate()
					geom=pcc.get_triangle_geometry()
					mxy=geom[:,1].mean()
					mz=geom[:,2].mean()
					v=np.arctan(np.sqrt(geom[:,0]))*180/np.pi
					mv=v.mean()
					print("   z-span:   %.2f %.2f" %(z1,z2))
					print("   Mean xy-bbox:   %.3f m" %mxy)
					print("   Mean  z-bbox:   %.3f m" %mz)
					print("   Mean abs-slope: %.2f dg" %mv)
					print("   Std. dev      : %.2f dg" %np.std(v))
				if c==c_expect:
					f_expect=f_c
		if ds_report is not None:
			report.report_class_check(ds_report,kmname,c_expect,f_expect,n_all,ogr_geom=polygon)
	ds_report=None		
			
		


	

if __name__=="__main__":
	main(sys.argv)
	