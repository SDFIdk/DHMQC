
WORK IN PROGRESS!!! 


import os,sys
DEBUG = "-debug" in sys.argv
import numpy as np
from triangle import triangle
from slash import slash
from osgeo import ogr
import shapely
import shapely.geometry as shg

unclass = 1
groundclass = 2
swathboundaryclass=3
lowpointnoiseclass=7


def count_points_inside_polygon(pointA, classA, this_class, poly):
	xmin,ymin,xmax,ymax=poly.bounds
	I=np.logical_and(np.logical_and((pointA>=(xmin,ymin)),(pointA<=(xmax,ymax))).all(axis=1),classA==this_class)
	#	I=np.where(I)[0]
	#if no points found, return 0
	if not I.any():
		return 0
	bpointA=pointA[I]
	mpoint=shg.MultiPoint(bpointA)
	print("Calculating intersection...")
	intersection=mpoint.intersection(poly)	
	if intersection.is_empty:
		ncp=0
	elif isinstance(intersection,shg.Point):
		ncp=1
	else:
		ncp=len(intersection.geoms)
	return ncp
	
#mypoints = np.array([(10,10),(20,20),(30,30),(40,40),(50,50),(60,60)])
#myclasses = np.array([2,2,2,2,1,2])
#mypoly= shapely.wkt.loads("POLYGON ((0 0, 0 45, 45 45, 45 0, 0 0))")
#mythisclass = 2
#mycount = count_points_inside_polygon(mypoints, myclasses, mythisclass, mypoly)
#print mycount 

def get_polys(path):
	ds=ogr.Open(path)
	layer=ds.GetLayer(0)
	nf=layer.GetFeatureCount()
	print("%d features in %s" %(nf,path))
	polys=[]
	for i in xrange(nf):
		feature=layer.GetNextFeature()
		geom=feature.GetGeometryRef()
		sgeom=loads(geom.ExportToWkb())
		if not sgeom.is_valid:
			print("WARNING: feature %d not valid!" %i)
		polys.append(sgeom)
	ds=None
	return polys


class pointcloud_class (object):
	pass
	
	
def main(args):
	lasname = args[1]
	polyname = args[2]
	#just to get the 1km_YYYY_XXX from the las filename... 
	b_lasname=os.path.splitext(os.path.basename(lasname))[0]
	#file is opened in sLASh
	lasf=slash.LasFile(lasname)
	# The las file is read into xy (planar coordinates), z (height) and c (classes)
    pointcloud = pointcloud_class()
	pointcloud.xy,pointcloud.z,pointcloud.c,pointcloud.pid=lasf.read_records()
	
	

	
	
	
if __name__=="__main__":
	main(sys.argv)	

sys.exit()	







def Usage():
	print("To run:\n%s <las_file> <polygon_file>" %os.path.basename(sys.argv[0]))
	sys.exit()


	
	
	

def GetPoints(path):
	if len(path)==0:
		print("loading npy..")
		points=np.load("tmp1.npy")
		classes=np.load("tmp2.npy")
		print("DOne...")
	else:
		f=LasFile.File(path)
		points=[]
		classes=[]
		n=0
		for p in f:
			points.append((p.x,p.y,p.z))
			classes.append(p.classification)
			n+=1
			if n%2000==0:
				print n
			#if n>1e6:
			#	break
		points=np.array(points)
		classes=np.array(classes,dtype=np.uint8)
		print("%d points loaded from %s" %(points.shape[0],path))
		print("Extent: %s, %s" %(points.min(axis=0),points.max(axis=0)))
		print("Unique classes: %s" %np.unique(classes))
		np.save("tmp1.npy",points)
		np.save("tmp2.npy",classes)
	return points,classes



def GetBuildings(path):
	ds=ogr.Open(path)
	layer=ds.GetLayer(0)
	nf=layer.GetFeatureCount()
	print("%d features in %s" %(nf,path))
	polys=[]
	for i in xrange(nf):
		feature=layer.GetNextFeature()
		geom=feature.GetGeometryRef()
		sgeom=loads(geom.ExportToWkb())
		if not sgeom.is_valid:
			print("WARNING: feature %d not valid!" %i)
		polys.append(sgeom)
	ds=None
	return polys




def GetStats(points,classes,polys,check_these_classes=[1,2,6]):
	points=points[:,:2]
	nc={}
	npoly=0
	for poly in polys:
		npoly+=1	
		print("%s\n" %("*"*60))
		print("Processing feature...")
		xmin,ymin,xmax,ymax=poly.bounds
		print("Polygon 'bounds': %.4f %.4f %.4f %.4f" %(xmin,ymin,xmax,ymax))
		I=np.logical_and((points>=(xmin,ymin)),(points<=(xmax,ymax))).all(axis=1)
		I=np.where(I)[0]
		if I.size==0:
			print("No points in extent....")
			nc[npoly]=[0]*len(check_these_classes)
			continue
		boxpoints=points[I]
		boxclasses=classes[I]
		print("Points in polygon extent: %d" %boxpoints.shape[0])
		nc[npoly]=[]
		for c in check_these_classes:
			print("%s\n" %("#"*60))
			print("Looking at class %d..." %c)
			I=np.where(boxclasses==c)[0]
			if I.size==0:
				print("No points of class %d in extent..." %c)
				nc[npoly].append(0)
				continue
			cpoints=boxpoints[I]
			print("Points of class %d in polygon extent: %d" %(c,cpoints.shape[0]))
			multipoint=shg.MultiPoint(cpoints)
			print("Calculating intersection...")
			intersection=multipoint.intersection(poly)
			print("Geomtry type of intersection: %s" %intersection.geom_type)
			if intersection.is_empty:
				ncp=0
			elif (isinstance(intersection,shg.collection.GeometryCollection) or isinstance(intersection,shg.MultiPoint)):
				ncp=len(intersection.geoms)
			elif isinstance(intersection,shg.Point):
				ncp=1
			else:
				ncp=-1
				print("Unknown intersection type....")
			print("Points of class %d in polygon: %d"  %(c,ncp))
			nc[npoly].append(ncp)
		
	return nc
		
	

def main(args):
	laspath=args[1]
	polypath=args[2]
	points,classes=GetPoints(laspath)
	polys=GetBuildings(polypath)
	_classes=[2,1,6]
	ncs=GetStats(points,classes,polys,_classes)
	print("\n***************Summary:\n")
	for poly in ncs:
		nc=ncs[poly]
		print("Polygon: %d" %poly)
		total=sum(nc)
		if total==0:
			print("No points...")
			continue
		for i in range(len(_classes)):
			c=nc[i]
			f=float(c)/total
			print("Class %d: %d, fraction: %.3f" %(_classes[i],c,f))
	

if __name__=="__main__":
	main(sys.argv)
	