###########################
## beginnings of building zcheck...
#########################
import sys,os
import numpy as np
from thatsDEM import pointcloud,vector_io,array_geometry,report
unclassified=1
xy_tolerance=1.0
z_tolerance=1.2

def get_stats(dz):
	m=dz.mean()
	sd=np.std(dz)
	l1=np.fabs(dz).mean()
	print("Number of points: %d" %dz.shape[0])
	print("Mean dz:          %.4f m" %m)
	print("Std. dev of dz:   %.4f" %sd)
	print("Mean abs. error:  %.4f m" %l1)
	return m,sd,l1


def main(args):
	lasname=args[1]
	buildname=args[2]
	pc=pointcloud.fromLAS(lasname)
	polygons=map(array_geometry.ogrpoly2array,vector_io.get_geometries(buildname))
	pcs=dict()
	for id in pc.get_pids():
		print("%s\n" %("+"*70))
		print("Strip id: %d" %id)
		pcs[id]=pc.cut_to_strip(id).cut_to_class(unclassified)
		pcs[id].triangulate()
		pcs[id].calculate_validity_mask(60,1,1)
	del pc
	done=[]
	for id1 in pcs:
		pc1=pcs[id1]
		if pc1.get_size<100:
			print("Few points in strip %d. Continuing..." %id1)
			continue
		for id2 in pcs:
			print("%s\n" %("-"*70))
			print("Checking strip %d against strip %d" %(id1,id2))
			pc2=pcs[id2]
			if id1==id2:
				continue
			if not pc1.might_overlap(pc2):
				print("Strip %d and strip %d does not seem to overlap. Continuing..." %(id1,id2))
				continue
			fn=0
			for polygon in polygons:
				fn+=1
				print("%s\n" %("*"*70))
				bbox=array_geometry.get_bounds(polygon)
				if  not (pc1.might_intersect_box(bbox) and pc2.might_intersect_box(bbox)):
					print("Polygon not in strip overlap. Continuing...")
					continue
				pc2_in_poly=pc2.cut_to_polygon(polygon)
				if pc2_in_poly.get_size()<5:
					print("Not enough points ( %d ) from strip %d in building." %(pc2_in_poly.get_size(),id2))
					continue
				z_out=pc1.controlled_interpolation(pc2_in_poly.xy,nd_val=-999)
				M=(z_out!=-999)
				if not M.any():
					print("No points in proper triangles..")
					continue
				z_good=pc2_in_poly.z[M]
				dz=z_out[M]-z_good
				print("Statistics for check of strip %d against strip %d, feature %d" %(id1,id2,fn))
				m,sd,l1=get_stats(dz)
				#report

if __name__=="__main__":
	main(sys.argv)
				
				
				
				
		
	
	