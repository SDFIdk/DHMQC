#############################
## zcheck base script called by zcheck_build and 
## zcheck_road
#############################
import sys,os
import numpy as np
from thatsDEM import pointcloud,vector_io,array_geometry,report
from utils.names import get_1km_name
from utils.stats import get_dz_stats

def check_feature(pc1,pc2_in_poly,a_geom,DEBUG=False):
	z_out=pc1.controlled_interpolation(pc2_in_poly.xy,nd_val=-999)
	M=(z_out!=-999)
	if not M.any():
		return None
	z_good=pc2_in_poly.z[M]
	dz=z_out[M]-z_good
	#TODO calculate mean slope for triangles used - easy enough....
	m,sd,l1,n=get_dz_stats(dz)
	return m,sd,n #consider using also l1....
	

#buffer_dist not None signals that we are using line strings, so use cut_to_line_buffer
#report layer should be report.Z_CHECK_ROAD_TABLE for lines and Z_CHECK_BUILD_TABLE for polygons
def zcheck_base(lasname,vectorname,angle_tolerance,xy_tolerance,z_tolerance,cut_class,buffer_dist=None,report_layer_name=None,use_local=False,DEBUG=False):
	kmname=get_1km_name(lasname)
	pc=pointcloud.fromLAS(lasname)
	geometries=vector_io.get_geometries(vectorname)
	ds_report=None
	if report_layer_name is not None:
		ds_report=report.get_output_datasource(use_local)
		if ds_report is not None:
			if use_local:
				print("Using local data source for reporting.")
			else:
				print("Using global data source for reporting.")
	else:
		print("Will not do reporting - layer name is None")
	pcs=dict()
	for id in pc.get_pids():
		print("%s\n" %("+"*70))
		print("Strip id: %d" %id)
		pc_=pc.cut_to_strip(id).cut_to_class(cut_class)
		if pc_.get_size()>50:
			pcs[id]=pc_
			pcs[id].triangulate()
			pcs[id].calculate_validity_mask(angle_tolerance,xy_tolerance,z_tolerance)
		else:
			print("Not enough points....")
		
	del pc
	done=[]
	for id1 in pcs:
		pc1=pcs[id1]
		for id2 in pcs:
			if id1==id2 or (id1,id2) in done or (id2,id1) in done:
				continue
			done.append((id1,id2))
			ml="-"*70
			print("%s\nChecking strip %d against strip %d\n%s" %(ml,id1,id2,ml))
			pc2=pcs[id2]
			if not pc1.might_overlap(pc2):
				if DEBUG:
					print("Strip %d and strip %d does not seem to overlap. Continuing..." %(id1,id2))
					print("DEBUG: Strip1 bounds:\n%s\nStrip2 bounds:\n%s" %(pc1.get_bounds(),pc2.get_bounds())) 
				continue
			fn=0
			for ogr_geom in geometries:
				fn+=1
				a_geom=array_geometry.ogrgeom2array(ogr_geom)
				if DEBUG:
					print("----- feature: %d ------" %fn)
				bbox=array_geometry.get_bounds(a_geom)
				if  not (pc1.might_intersect_box(bbox) and pc2.might_intersect_box(bbox)):
					if DEBUG:
						print("Feature not in strip overlap. Continuing...")
						print("DEBUG: Strip1 bounds:\n%s\nStrip2 bounds:\n%s\nPolygon bounds:\n%s" %(pc1.get_bounds(),pc2.get_bounds(),bbox)) 
					continue
				
				
				if buffer_dist is not None:
					pc2_in_poly=pc2.cut_to_line_buffer(a_geom,buffer_dist)
				else:
					pc2_in_poly=pc2.cut_to_polygon(a_geom)
				print("(%d,%d,%d):" %(id1,id2,fn))
				if pc2_in_poly.get_size()>5:
					stats12=check_feature(pc1,pc2_in_poly,DEBUG)
				else:
					stats12=None
					print("Not enough points ( %d ) from strip %d in 'feature' (polygon / buffer)." %(pc2_in_poly.get_size(),id2))
				
				if buffer_dist is not None:
					pc1_in_poly=pc1.cut_to_line_buffer(a_geom,buffer_dist)
				else:
					pc1_in_poly=pc1.cut_to_polygon(a_geom)
				
				print("(%d,%d,%d):" %(id2,id1,fn))
				if pc1_in_poly.get_size()>5:
					stats21=check_feature(pc2,pc1_in_poly,DEBUG)
				else:
					stats21=None
					print("Not enough points ( %d ) from strip %d in 'feature' (polygon / buffer)." %(pc1_in_poly.get_size(),id1))
				if ds_report is not None and (stats12 is not None or stats21 is not None):
					report.report_zcheck(ds_report,kmname,id1,id2,stats12,stats21,ogr_geom=ogr_geom,table=report_layer_name)
	ds_report=None
	return len(done)
	