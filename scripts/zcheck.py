import sys,os
import numpy as np
import shapely.geometry as shg
from shapely.wkb import loads
from triangle import triangle
from slash import slash
from osgeo import ogr
import matplotlib.pyplot as plt

groundclass = 5
roadbuf = 3
xy_tri_bbox_size = 8
z_tri_bbox_size = 4



#Trianguler alle striber
#For alle striber(s punkter p_i=1 til n), goer...
#Ligger p_i taet paa vej-vertice?
#Hvis ja, interpoler 
#opsaml i array (punkt_id, fra_stribe, maalt z, interpoleret z)



ds = ogr.Open(sys.argv[2])

if True:
	# pointer to file. 
	lasf=slash.LasFile(sys.argv[1])

	# header of las file is read and the number of points are printed
	print("%d points in %s" %(lasf.get_number_of_records(),sys.argv[1]))

	# The las file is read into xy (planar coordinates), z (height) and c (classes)
	xy,z,c,pid=lasf.read_records()

	lasf.close()

	#Empty dictionary defined
	triangulations = dict()

	for id in np.unique(pid):
		print("\n%s\n" %("*"*80))
		print("Triangulating ground points from strip %d" %id)
		#numpy is used to return an array where point source id is the current number and class 2 (ground)
#		I=np.where(np.logical_and(pid==id, c==2))[0]
		I=np.where(np.logical_and(pid==id, c==groundclass))[0]
		if I.size <100: 
			continue
		xyi = xy[I]
		zi  =  z[I]
		tri = triangle.Triangulation(xyi)
		tri.basez = zi
		triangulations[id]=tri
		
	#We are being nice - cleaning up!
	del xy
	del z
	del c
	del pid
	buffers=[]
	layer = ds.GetLayer(0)	
	nfeatures=layer.GetFeatureCount()
	print("%d features in %s" %(nfeatures,sys.argv[2]))
	for nf in range(nfeatures):
		print("\n%s\n" %("*"*80))
		feature=layer.GetNextFeature()
		geom=feature.GetGeometryRef()
		sgeom=loads(geom.ExportToWkb())
		if not sgeom.is_valid:
			print("WARNING: feature %d not valid!" %i)
			continue
		print("Feature %d, Geometry type: %s" %(nf+1,sgeom.geom_type))
		L=sgeom.length
		print("Length: %.2f" %L)
		if L<1:
			continue
		buf=sgeom.buffer(roadbuf)
		#TODO: now we should really select all strips that have intersection with this buffer and then check (pair) combinations of those...
		print("Just checking - area of buffer: %.2f, valid: %s" %(buf.area,buf.is_valid))
		buffers.append(buf)
	#close datasource
	ds=None
	n_buf=0
	for buf in buffers:
		n_buf+=1
		print("\n%s\n" %("*"*80))
		print("Looking at buffer: %d" %n_buf)
		print("Buffer bounds: %s" %str(buf.bounds))
		#find the strips, which might intersect this buffer
		ids=dict()
		for id in triangulations:
			xmin,ymin=np.min(triangulations[id].points,axis=0)
			xmax,ymax=np.max(triangulations[id].points,axis=0)
			pc_box=shg.box(xmin,ymin,xmax,ymax)
			if pc_box.intersects(buf):
				ids[id]=pc_box
		
		print("Found %d strips, %s, which MIGHT intersect buffer." %(len(ids),ids))
		if len(ids)<2:
			print("Not enough intersections... continuing")
			continue
		for id1 in ids:
			tri1=triangulations[id1]
			for id2 in ids:
				if id1==id2:
					continue
				tri2=triangulations[id2]
				print("\n%s\n" %("-"*80))
				print("Checking strip %d against strip %d..." %(id1,id2))
				print("Creating multipoint geometry and intersection with buffer...")
				#Cut down to intersection and construct 2.5D multipoint set
				strip_intersection=ids[id1].intersection(ids[id2])
				if strip_intersection.is_empty:
					print("Strip1: %s, Strip2: %s" %(str(ids[id1].bounds),str(ids[id2]).bounds))
					print("No overlap between strips...")
					continue
				if (not buf.intersects(strip_intersection)):
					print("No overlap between intersection and buffer...")
					continue
				xmin,ymin,xmax,ymax=strip_intersection.bounds
				M=np.logical_and((tri2.points>=(xmin,ymin)),(tri2.points<=(xmax,ymax))).all(axis=1)
				crop_xyz=np.column_stack((tri2.points[M],tri2.basez[M])).tolist()
				print("Cropping .. points in strip intersection rectangle: %d" %len(crop_xyz))
				multipoint=shg.MultiPoint(crop_xyz)
				print "Multipoint bounds ", multipoint.bounds, multipoint.has_z
				in_buf=multipoint.intersection(buf)
				if in_buf.is_empty:
					print("No points from strip %d in this buffer..." %id2)
					continue
				print("Geomtry type of intersection: %s" %in_buf.geom_type)
				nib=len(in_buf.geoms)
				print("%d points in intersection" %nib)
				print("Has z: %s" %in_buf.has_z)
				if nib>1:
					print("TODO: fetch coords effectively...")
					in_buf_xy=np.empty((nib,2),dtype=np.float64)
					in_buf_z=np.empty((nib,),dtype=np.float64)
					for i in xrange(nib):
						pt=in_buf.geoms[i]
						in_buf_xy[i]=(pt.x,pt.y)
						in_buf_z[i]=pt.z
					#print in_buf_xy.shape,np.min(in_buf_xy,axis=0),np.min(in_buf_z),np.max(in_buf_z)
#					itriangles=tri1.find_appropriate_triangles(tri1.basez,in_buf_xy,2.0,0.3)
					itriangles=tri1.find_appropriate_triangles(tri1.basez,in_buf_xy,xy_tri_bbox_size,z_tri_bbox_size)
					I=np.where(itriangles!=-1)[0]
					if (I.size==0):
						print("All points in 'bad' triangles...")
						continue
					itriangles=itriangles[I]
					in_buf_xy=in_buf_xy[I]
					in_buf_z=in_buf_z[I]
					nd_val=-999
					z_out=tri1.interpolate(tri1.basez,in_buf_xy,nd_val)
					print("We have %d points interpolated..." %z_out.shape[0])
					dz=z_out-in_buf_z
					I=np.where(np.fabs(dz)<0.3)[0]
					if I.size==0:
						print("No points with abs-diff < tolerance...")
						continue
					J=np.where(np.fabs(dz)>=0.3)[0]
					z_out_g=z_out[I]
					in_buf_z_g=in_buf_z[I]
					in_buf_xy_g=in_buf_xy[I]
					dz=z_out_g-in_buf_z_g
					in_buf_xy_b=in_buf_xy[J]
					print("Buffer: %d, strip1: %d, strip2: %d" %(n_buf,id1,id2))
					print("Mean dz: %.4f m" %dz.mean())
					print("Std. dev of dz:          %.4f" %np.std(dz))
					print("Mean abs. error: %.4f m" %np.fabs(dz).mean())
					
					plt.figure()
					pcname=os.path.basename(sys.argv[1])
					plt.title("PC: %s, buffer: %d, strip1: %d, strip2: %d" %(pcname,n_buf,id1,id2))
					plt.hist(dz)
					outname=os.path.splitext(pcname)[0]+"_%d_%d_%d.png" %(n_buf,id1,id2)
					outname=os.path.join(sys.argv[3],outname)
					plt.savefig(outname)
					plt.figure()
					triangles=tri1.get_triangles(itriangles)
					plt.triplot(tri1.points[:,0],tri1.points[:,1],triangles)
					plt.plot(in_buf_xy_g[:,0],in_buf_xy_g[:,1],".",color="blue")
					if J.size>0:
						itriangles=tri1.find_triangles(in_buf_xy_b)
						triangles=tri1.get_triangles(itriangles)
						plt.triplot(tri1.points[:,0],tri1.points[:,1],triangles)
						plt.plot(in_buf_xy_b[:,0],in_buf_xy_b[:,1],".",color="red")
					#outname=os.path.splitext(pcname)[0]+"_tri_%d_%d_%d.png" %(n_buf,id1,id2)
					#outname=os.path.join(sys.argv[3],outname)
					#plt.savefig(outname)
					plt.show()
					plt.close("all")
					



	
	


	

# python zcheck.py C:\dev\dhmqc\demo\1km_6165_449.las C:\dev\dhmqc\demo\1km_6165_449.shp out_dir



#python zcheck.py ..\demo\2007_1km_6165_449.las ..\demo\1km_6165_449.shp .	
	
	
	
	


