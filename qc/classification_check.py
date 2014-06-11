###########################
## beginnings of building classification check
#########################
import sys,os,time
import dhmqc_constants as constants
import numpy as np
from thatsDEM import pointcloud,vector_io,array_geometry,report
from utils.names import get_1km_name
#Sensible z-limits for detecting when a 3d-feature seems to be OK. Used in below_poly
SENSIBLE_Z_MIN=0
SENSIBLE_Z_MAX=200

DEBUG="-debug" in sys.argv



def usage():
	print("Call:\n%s <las_file> <polygon_file> -type <poly_type> -below_poly -use_local" %os.path.basename(sys.argv[0]))
	print("Use -type <poly_type> to specify the type of polygon, e.g. building, lake, bridge.")
	print("Use -below_poly to restrict to points which lie below the mean z of the input polygon(s).")
	print("This ONLY makes sense for 3D input polygons AND will override the -type argument to 'below_poly'")
	print("Use -use_local to force use of local database for reporting.")
	sys.exit()

def main(args):
	if len(args)<3:
		usage()
	lasname=args[1]
	buildname=args[2]
	if "-below_poly" in args:
		below_poly=True
		ptype="below_poly"
	else:
		below_poly=False
		if "-type" in args:
			i=args.index("-type")
			ptype=args[i+1].lower()
		else:
			ptype="undefined"
	kmname=get_1km_name(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	if below_poly:
		print("Only using points which lie below polygon mean z!")
	pc=pointcloud.fromLAS(lasname)
	print("Classes in pointcloud: %s" %pc.get_classes())
	polygons=vector_io.get_geometries(buildname)
	nf=0
	use_local="-use_local" in args
	reporter=report.ReportClassCheck(use_local) #ds_report=report.get_output_datasource(use_local)
	for polygon in polygons:
		if below_poly:
			if polygon.GetCoordinateDimension()<3:
				print("Error: polygon not 3D - below_poly does not make sense!")
				continue
			a_polygon3d=array_geometry.ogrpoly2array(polygon,flatten=False)[0]
			mean_z=a_polygon3d[:,2].mean()
			if mean_z<SENSIBLE_Z_MIN or mean_z>SENSIBLE_Z_MAX:
				print("Warning: This feature seems to have unrealistic mean z value: {0:.2f} m".format(mean_z))
				continue
			del a_polygon3d
		else:
			mean_z=-1
		polygon.FlattenTo2D()
		nf+=1
		ml="-"*70
		print("%s\nFeature %d\n%s" %(ml,nf,ml))
		a_polygon=array_geometry.ogrpoly2array(polygon)
		pc_in_poly=pc.cut_to_polygon(a_polygon)
		if below_poly:
			pc_in_poly=pc_in_poly.cut_to_z_interval(-999,mean_z)
		n_all=pc_in_poly.get_size()
		freqs=[0]*(len(constants.classes)+1)  #list of frequencies...
		if n_all>0:
			c_all=pc_in_poly.get_classes()
			if below_poly and DEBUG:
				print("Mean z of polygon is:        %.2f m" %mean_z)
				print("Mean z of points below is:   %.2f m" %pc_in_poly.z.mean())
			print("Number of points in polygon:  %d" %n_all)
			print("Classes in polygon:           %s" %(str(c_all)))
			#important for reporting that the order here is the same as in the table definition in report.py!!
			n_found=0
			for i,c in enumerate(constants.classes):
				if c in c_all:
					pcc=pc_in_poly.cut_to_class(c)
					n_c=pcc.get_size()
					f_c=n_c/float(n_all)
					n_found+=n_c
					print("Class %d::" %c)
					print("   #Points:  %d" %n_c)
					print("   Fraction: %.3f" % f_c)
					freqs[i]=f_c
			f_other=(n_all-n_found)/float(n_all)
			freqs[-1]=f_other
		send_args=[kmname]+freqs+[n_all,ptype]
		reporter.report(*send_args,ogr_geom=polygon)
		
			
		


	

if __name__=="__main__":
	main(sys.argv)
	