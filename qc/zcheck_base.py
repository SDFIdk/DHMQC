# Copyright (c) 2015, Danish Geodata Agency <gst@gst.dk>
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
## zcheck base script called by zcheck_build and 
## zcheck_road
#############################
import sys,os,time
import numpy as np
from thatsDEM import pointcloud,vector_io,array_geometry
from db import report
import dhmqc_constants as constants
from utils.stats import get_dz_stats
DEBUG="-debug" in sys.argv

def check_feature(pc1,pc2_in_poly,a_geom,DEBUG=False):
	z_out=pc1.controlled_interpolation(pc2_in_poly.xy,nd_val=-999)
	M=(z_out!=-999)
	z_good=pc2_in_poly.z[M]
	if z_good.size<2:
		return None
	dz=z_out[M]-z_good
	m,sd,l1,rms,n=get_dz_stats(dz)
	return m,sd,rms,n #consider using also l1....
	

#buffer_dist not None signals that we are using line strings, so use cut_to_line_buffer
def zcheck_base(lasname,vectorname,angle_tolerance,xy_tolerance,z_tolerance,cut_class,reporter,buffer_dist=None,layername=None,layersql=None):
	is_roads=buffer_dist is not None #'hacky' signal that its roads we're checking
	print("Starting zcheck_base run at %s" %time.asctime())
	tstart=time.clock()
	kmname=constants.get_tilename(lasname)
	pc=pointcloud.fromLAS(lasname)
	t2=time.clock()
	tread=t2-tstart
	print("Reading data took %.3f ms" %(tread*1e3))
	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception,e:
		print("Could not get extent from tilename.")
		extent=None
	geometries=vector_io.get_geometries(vectorname,layername,layersql,extent)
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
			overlap_box=array_geometry.bbox_intersection(pc1.get_bounds(),pc2.get_bounds()) #shouldn't be None
			fn=0
			for ogr_geom in geometries:
				fn+=1
				try:
					a_geom=array_geometry.ogrgeom2array(ogr_geom)
				except Exception,e:
					print(str(e))
					continue
				if DEBUG:
					print("----- feature: %d ------" %fn)
				bbox=array_geometry.get_bounds(a_geom)
				
				if  not (pc1.might_intersect_box(bbox) and pc2.might_intersect_box(bbox)):
					if DEBUG:
						print("Feature not in strip overlap. Continuing...")
						print("DEBUG: Strip1 bounds:\n%s\nStrip2 bounds:\n%s\nPolygon bounds:\n%s" %(pc1.get_bounds(),pc2.get_bounds(),bbox)) 
					continue
				#possibly cut the geometry into pieces contained in 'overlap' bbox
				pieces=[ogr_geom]
				dim=ogr_geom.GetDimension()
				assert(dim==1 or dim==2)  #only line or polygons
				if dim==1:
					cut_geom=array_geometry.cut_geom_to_bbox(ogr_geom,overlap_box)
					n_geoms=cut_geom.GetGeometryCount()
					if n_geoms>0:
						pieces=[cut_geom.GetGeometryRef(ng).Clone() for ng in xrange(n_geoms)]
						print("Cut line into %d pieces..." %n_geoms)
				
				for geom_piece in pieces:
					a_geom=array_geometry.ogrgeom2array(geom_piece) 
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
					
					if dim==1:
						pc1_in_poly=pc1.cut_to_line_buffer(a_geom,buffer_dist)
					else:
						pc1_in_poly=pc1.cut_to_polygon(a_geom)
					
					print("(%d,%d,%d):" %(id2,id1,fn))
					if pc1_in_poly.get_size()>5:
						stats21=check_feature(pc2,pc1_in_poly,DEBUG)
					else:
						stats21=None
						print("Not enough points ( %d ) from strip %d in 'feature' (polygon / buffer)." %(pc1_in_poly.get_size(),id1))
					if (stats12 is not None or stats21 is not None):
						c_prec=0
						n_points=0
						args12=[None]*4
						args21=[None]*4
						if stats12 is not None:
							n_points+=stats12[3]
							args12=stats12
						if stats21 is not None:
							n_points+=stats21[3]
							args21=stats21
						if stats12 is not None:
							c_prec+=(stats12[2])*(stats12[3]/float(n_points))
						if stats21 is not None:
							c_prec+=(stats21[2])*(stats21[3]/float(n_points))
						#Combined prec. now uses RMS-value.... Its simply a weightning of the two RMS'es...
						#TODO: consider setting a min bound for the combined number of points.... or a 'confidence' weight...
						args=[kmname,id1,id2]
						for i in range(4):
							args.extend([args12[i],args21[i]])
						args.append(c_prec)
						t1=time.clock()
						reporter.report(*args,ogr_geom=geom_piece)
						t2=time.clock()
						print("Reporting took %.4s ms - concurrency?" %((t2-t1)*1e3))
	tend=time.clock()
	tall=tend-tstart
	frac_read=tread/tall
	print("Finished checking tile, time spent: %.3f s, fraction spent on reading las data: %.3f" %(tall,frac_read))
	return len(done)
	