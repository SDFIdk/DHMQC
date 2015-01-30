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

def read(path,attrs=[]):
	ds=ogr.Open(path)
	if ds is None:
		return []
	layer=ds.GetLayer(0)
	nf=layer.GetFeatureCount()
	feats=[]
	print("%d feature(s) in %s" %(nf,path))
	for i in xrange(nf):
		feature=layer.GetNextFeature()
		feats.appen(feature)
	ds=None
	return feats
	