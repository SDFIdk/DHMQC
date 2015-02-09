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
## Stuff to read / burn vector layers
#########################

from osgeo import ogr, gdal
import numpy as np
import time



def burn_vector_layer(cstr,georef,shape,layername=None,layersql=None):
	#For now just burn a mask - can be expanded to burn attrs. by adding keywords.
	#input a GDAL-style georef
	#If executing fancy sql like selecting buffers etc, be sure to add a where ST_Intersects(geom,TILE_POLY) - otherwise its gonna be slow....
	ds=ogr.Open(cstr)
	if ds is None:
		raise Exception("Failed to open "+cstr)
	if layersql is not None: #an sql statement will take precedence
		layer=ds.ExecuteSQL(layersql)
	elif layername is not None:  #then a layername
		layer=ds.GetLayerByName(layername)
	else: #fallback - shapefiles etc, use first layer
		layer=ds.GetLayer(0)
		assert(layer is not None)
	#this aint needed if filter is already set in sql_statement
	extent=(georef[0],georef[3]+shape[1]*georef[5],georef[0]+shape[0]*georef[1],georef[3]) #x1,y1,x2,y2
	layer.SetSpatialFilterRect(*extent)
	mem_driver=gdal.GetDriverByName("MEM")
	mask_ds=mem_driver.Create("dummy",int(shape[1]),int(shape[0]),1,gdal.GDT_Byte)
	mask_ds.SetGeoTransform(georef)
	mask=np.zeros(shape,dtype=np.bool)
	mask_ds.GetRasterBand(1).WriteArray(mask) #write zeros to output
	#mask_ds.SetProjection('LOCAL_CS["arbitrary"]')
	ok=gdal.RasterizeLayer(mask_ds,[1],layer,burn_values=[1],options=['ALL_TOUCHED=TRUE'])
	A=mask_ds.ReadAsArray()
	if layersql is not None:
		ds.ReleaseResultSet(layer)
	layer=None
	ds=None
	return A

def get_geometries(cstr, layername=None, layersql=None, extent=None):
	#If executing fancy sql like selecting buffers etc, be sure to add a where ST_Intersects(geom,TILE_POLY) - otherwise its gonna be slow....
	t1=time.clock()
	ds=ogr.Open(cstr)
	if ds is None:
		raise Exception("Failed to open "+cstr)
	if layersql is not None: #an sql statement will take precedence
		layer=ds.ExecuteSQL(layersql)
	elif layername is not None:  #then a layername
		layer=ds.GetLayerByName(layername)
	else: #fallback - shapefiles etc, use first layer
		layer=ds.GetLayer(0)
	assert(layer is not None)
	if extent is not None:
		layer.SetSpatialFilterRect(*extent)
	else:
		layer.SetSpatialFilterRect(None) #reset
	nf=layer.GetFeatureCount()
	print("%d feature(s) in layer %s" %(nf,layer.GetName()))
	geoms=[]
	for i in xrange(nf):
		feature=layer.GetNextFeature()
		geom=feature.GetGeometryRef().Clone()
		#Handle multigeometries here...
		t=geom.GetGeometryType()
		ng=geom.GetGeometryCount()
		geoms_here=[geom]
		if ng>1:
			if t!=ogr.wkbPolygon and t!=ogr.wkbPolygon25D:
				#so must be a multi-geometry
				geoms_here=[geom.GetGeometryRef(i).Clone() for i in range(ng)]
		geoms.extend(geoms_here)

	if layersql is not None:
		ds.ReleaseResultSet(layer)
	layer=None
	ds=None
	t2=time.clock()
	print("Fetching geoms took %.3f s" %(t2-t1))
	return geoms


	