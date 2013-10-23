import sys,os 
DEBUG = "-debug" in sys.argv
import numpy as np
import shapely.geometry as shg
from shapely.wkb import loads,dumps
from thatsDEM import triangle,slash,array_geometry, report
from osgeo import ogr
if DEBUG:
	import matplotlib.pyplot as plt


groundclass = 5
groundclass2 = 11
roadbuf = 2
xy_tri_bbox_size = 2.5
z_tri_bbox_size = 1

#Trianguler alle striber
#For alle striber(s punkter p_i=1 til n), goer...
#Ligger p_i taet paa vej-vertice?
#Hvis ja, interpoler 
#opsaml i array (punkt_id, fra_stribe, maalt z, interpoleret z)

def get_stats(dz):
	m=dz.mean()
	sd=np.std(dz)
	l1=np.fabs(dz).mean()
	print("Mean dz: %.4f m" %m)
	print("Std. dev of dz:          %.4f" %sd)
	print("Mean abs. error: %.4f m" %l1)
	return m,sd,l1

def check_strip_overlap(tri1,tri2,segment,bbox_intersection):
	segment_coords=np.array(segment)
	xmin,ymin,xmax,ymax=bbox_intersection
	print("Cropping ...")
	M=np.logical_and((tri2.points>=(xmin,ymin)),(tri2.points<=(xmax,ymax))).all(axis=1)
	crop_xy=tri2.points[M]
	crop_z=tri2.basez[M]
	print("#points in strip intersection rectangle: %d" %crop_xy.shape[0])
	M=array_geometry.points_in_buffer(crop_xy,segment_coords,roadbuf)
	if M.any():
		print("Fetch coords effectively... -done!")
		in_buf_xy=crop_xy[M]
		in_buf_z=crop_z[M]
		itriangles=tri1.find_appropriate_triangles(tri1.basez,in_buf_xy,xy_tri_bbox_size,z_tri_bbox_size)
		I=np.where(itriangles!=-1)[0]
		if (I.size==0):
			print("All points in 'bad' triangles...")
			return None
		itriangles=itriangles[I]
		in_buf_xy=in_buf_xy[I]
		in_buf_z=in_buf_z[I]
		nd_val=-999
		z_out=tri1.interpolate(tri1.basez,in_buf_xy,nd_val)
		print("We have %d points interpolated..." %z_out.shape[0])
		dz=z_out-in_buf_z
		J=np.where(np.fabs(dz)>=0.3)[0]
		in_buf_xy_b=in_buf_xy[J]
		
		if DEBUG:
			plt.figure()
			triangles=tri1.get_triangles(itriangles)
			plt.triplot(tri1.points[:,0],tri1.points[:,1],triangles)
			plt.plot(in_buf_xy_g[:,0],in_buf_xy_g[:,1],".",color="blue")
			if J.size>0:
				itriangles=tri1.find_triangles(in_buf_xy_b)
				triangles=tri1.get_triangles(itriangles)
				plt.triplot(tri1.points[:,0],tri1.points[:,1],triangles)
				plt.plot(in_buf_xy_b[:,0],in_buf_xy_b[:,1],".",color="red")
					
			plt.show()
			plt.close("all")
		return dz
	return None

def Usage():
	print("To run:\n%s <las_file> <road_line_string_file> <outdir>" %os.path.basename(sys.argv[0]))
	print("Last argument is optional - if given output histrograms will be saved here.")
	sys.exit()


def main(args):
	if len(args)<3:
		Usage()
	# pointer to files
	lasname=args[1]
	roadname=args[2]
	if len(args)>3:
		outdir=args[3]
		if not os.path.exists(outdir):
			os.mkdir(outdir)
	else:
		outdir=None
	b_lasname=os.path.splitext(os.path.basename(lasname))[0]
	#TODO: we should make a function which extract 1km name and returns something useful if the name isn't there....
	i=b_lasname.find("1km")
	if i!=-1:
		kmname=b_lasname[i:]  #improve - see above....
	else:
		kmname=b_lasname
	lasf=slash.LasFile(lasname)
	ds = ogr.Open(roadname)
	if ds == None:
		print "Roadfile not found. Stopping"
		return
	# header of las file is read and the number of points are printed
	print("%d points in %s" %(lasf.get_number_of_records(),lasname))

	# The las file is read into xy (planar coordinates), z (height) and c (classes)
	ret=lasf.read_records()
	xy=ret["xy"]
	z=ret["z"]
	c=ret["c"]
	pid=ret["pid"]
	lasf.close()

	#Empty dictionary defined
	triangulations = dict()

	for id in np.unique(pid):
		print("\n%s\n" %("*"*80))
		print("Triangulating ground points from strip %d" %id)
		#numpy is used to return an array where point source id is the current number and class 2 (ground)
		I=np.where(np.logical_and(pid==id, c==2))[0]
		#REVERT THE NEXT LINE OF CODE ... JUST TO CHECK 2007 DATA
		#I=np.where(np.logical_or(np.logical_and(pid==id, c == groundclass),np.logical_and(pid==id, c == groundclass2)))[0]
		if I.size <100: 
			print("Few points. Continuing....")
			continue
		xyi = xy[I]
		zi  =  z[I]
		tri = triangle.Triangulation(xyi)
		tri.basez = zi
		triangulations[id]=tri
		
	#We are being nice - cleaning up!
	del ret
	print("\n%s\n" %("*"*80))
	segments=[]
	layer = ds.GetLayer(0)	
	nfeatures=layer.GetFeatureCount()
	print("%d features in %s" %(nfeatures,roadname))
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
		segments.append(sgeom)
	#close datasource
	ds=None
	n_buf=0
	for segment in segments:
		n_buf+=1
		print("\n%s\n" %("*"*80))
		print("Looking at LineString: %d" %n_buf)
		print("Bounds: %s" %str(segment.bounds))
		#find the strips, which might intersect this buffer / segment...
		#should we check intersection between the LineString or a buffer??
		ids=dict()
		for id in triangulations:
			xmin,ymin=np.min(triangulations[id].points,axis=0)
			xmax,ymax=np.max(triangulations[id].points,axis=0)
			pc_box=shg.box(xmin,ymin,xmax,ymax)
			if pc_box.intersects(segment.buffer(2.0)):
				ids[id]=pc_box
		
		print("Found %d strips, %s, which MIGHT intersect LineString" %(len(ids),ids.keys()))
		if len(ids)<2:
			print("Not enough intersections... continuing")
			continue
		done=[]
		for id1 in ids:
			tri1=triangulations[id1]
			for id2 in ids:
				if id1==id2 or (id1,id2) in done or (id2,id1) in done:
					continue
				done.extend([(id1,id2),(id2,id1)])
				tri2=triangulations[id2]
				print("\n%s\n" %("-"*80))
				print("Checking strip %d against strip %d..." %(id1,id2))
				#Cut down to intersection 
				strip_intersection=ids[id1].intersection(ids[id2])
				if strip_intersection.is_empty:
					print("Strip1: %s, Strip2: %s" %(str(ids[id1].bounds),str(ids[id2].bounds)))
					print("No overlap between strips...")
					continue
				if (not segment.intersects(strip_intersection)):
					print("No overlap between intersection and line string...")
					continue
				print("Segment: %d, strip1: %d, strip2: %d" %(n_buf,id1,id2))
				dz1=check_strip_overlap(tri1,tri2,segment,strip_intersection.bounds)
				#Move to report_stats....
				if (dz1 is not None):
					m,s,l1=get_stats(dz1)
					report.report_zcheck(kmname,id1,id2,m,s,wkb_geom=dumps(segment))
				print("%s" %("+"*80))
				print("Segment: %d, strip1: %d, strip2: %d" %(n_buf,id2,id1))
				dz2=check_strip_overlap(tri2,tri1,segment,strip_intersection.bounds)
				if (dz2 is not None):
					m,s,l1=get_stats(dz2)
					report.report_zcheck(kmname,id2,id1,m,s,wkb_geom=dumps(segment))
				if outdir is not None and DEBUG:
					plt.figure()
					plt.subplot(2,1,1)
					pcname=os.path.basename(lasname)
					plt.title("PC: %s, buffer: %d, strip1: %d, strip2: %d" %(pcname,n_buf,id1,id2))
					plt.hist(dz1)
					plt.subplot(2,1,2)
					plt.title("PC: %s, buffer: %d, strip1: %d, strip2: %d" %(pcname,n_buf,id2,id1))
					plt.hist(dz2)
					outname=os.path.splitext(pcname)[0]+"_%d_%d_%d.png" %(n_buf,id1,id2)
					outname=os.path.join(outdir,outname)
					plt.savefig(outname)
				
					
					
if __name__=="__main__":
	main(sys.argv)


	
	


	

# python zcheck.py C:\dev\dhmqc\demo\1km_6165_449.las C:\dev\dhmqc\demo\1km_6165_449.shp out_dir



#python zcheck.py ..\demo\2007_1km_6165_449.las ..\demo\1km_6165_449.shp .	
	
	
	
	


