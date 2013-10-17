import os,sys
import numpy as np
import liblas.file as LasFile
from osgeo import ogr
from shapely.wkb import loads
import shapely.geometry as shg
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
	