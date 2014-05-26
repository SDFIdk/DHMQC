#########################
## IO library functions...
#############

from osgeo import ogr


def get_geometries(path):
	ds=ogr.Open(path)
	if ds is None:
		return []
	layer=ds.GetLayer(0)
	nf=layer.GetFeatureCount()
	print("%d feature(s) in %s" %(nf,path))
	geoms=[]
	for i in xrange(nf):
		feature=layer.GetNextFeature()
		geom=feature.GetGeometryRef().Clone()
		if not geom.IsValid():
			print("WARNING: feature %d not valid!" %i)
			continue
		geoms.append(geom)
	ds=None
	return geoms

