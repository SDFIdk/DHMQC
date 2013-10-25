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

def main(args):
	lasname=args[1]
	buildname=args[2]
	kmname=get_1km_name(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	pc=pointcloud.fromLAS(lasname)
	print("Classes in pointcloud: %s" %pc.get_classes())
	polygons=vector_io.get_geometries(buildname)
	nf=0
	for polygon in polygons:
		nf+=1
		ml="-"*70
		print("%s\nFeature %d\n%s" %(ml,nf,ml))
		a_polygon=array_geometry.ogrpoly2array(polygon)
		pc_in_poly=pc.cut_to_polygon(a_polygon)
		n_all=pc_in_poly.get_size()
		if n_all>0:
			c_all=pc_in_poly.get_classes()
			print("Number of points in polygon:  %d" %n_all)
			print("Classes in polygon:           %s" %(str(c_all)))
			for c in c_all:
				pcc=pc_in_poly.cut_to_class(c)
				n_c=pcc.get_size()
				print("Class %d::" %c)
				print("   #Points:  %d" %n_c)
				print("   Fraction: %.3f" %(n_c/float(n_all)))
				z1,z2=pcc.get_z_bounds()
				print("   z-span:   %.2f %.2f" %(z1,z2))
			print("TODO: geometry check...")
			
		


	

if __name__=="__main__":
	main(sys.argv)
	