###########################
## beginnings of building classification check
#########################
import sys,os,time
import dhmqc_constants as constants
import numpy as np
from thatsDEM import pointcloud,vector_io,array_geometry,report
from utils.names import get_1km_name

DEBUG="-debug" in sys.argv



def usage():
	print("Call:\n%s <las_file> <polygon_file> -type <poly_type> -use_local" %os.path.basename(sys.argv[0]))
	print("Use -type <poly_type> to specify the type of polygon, e.g. building, lake, bridge.")
	print("Use -use_local to force use of local database for reporting.")
	sys.exit()

def main(args):
	if len(args)<3:
		usage()
	lasname=args[1]
	buildname=args[2]
	if "-type" in args:
		i=args.index("-type")
		ptype=args[i+1].lower()
	else:
		ptype="undefined"
	kmname=get_1km_name(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	pc=pointcloud.fromLAS(lasname)
	print("Classes in pointcloud: %s" %pc.get_classes())
	polygons=vector_io.get_geometries(buildname)
	nf=0
	use_local="-use_local" in args
	reporter=report.ReportClassCheck(use_local) #ds_report=report.get_output_datasource(use_local)
	if use_local:
		print("Using local data source for reporting.")
	else:
		print("Using global data source for reporting.")
	if reporter.ds is None:
		print("Failed to open report datasource - you might need to CREATE one...")
	for polygon in polygons:
		polygon.FlattenTo2D()
		nf+=1
		ml="-"*70
		print("%s\nFeature %d\n%s" %(ml,nf,ml))
		a_polygon=array_geometry.ogrpoly2array(polygon)
		pc_in_poly=pc.cut_to_polygon(a_polygon)
		n_all=pc_in_poly.get_size()
		freqs=[0]*(len(constants.classes)+1)  #list of frequencies...
		if n_all>0:
			c_all=pc_in_poly.get_classes()
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
	