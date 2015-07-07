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

EXTENT_WKT="WKT_EXT" #placeholder for tile-wkt


def open(cstr,layername=None,layersql=None,extent=None):
    ds=ogr.Open(cstr)
    if ds is None:
        raise Exception("Failed to open "+cstr)
    if layersql is not None: #an sql statement will take precedence
        if extent is not None and EXTENT_WKT in layersql:
            wkt="'POLYGON(("
            for dx,dy in ((0,0),(0,1),(1,1),(1,0)):
                wkt+="{0} {1},".format(str(extent[2*dx]),str(extent[2*dy+1]))
            wkt+="{0} {1}))'".format(str(extent[0]),str(extent[1]))
            layersql=layersql.replace(EXTENT_WKT,wkt)
        layer=ds.ExecuteSQL(str(layersql)) #restrict to ASCII encodable chars here - don't know what the datasource is precisely and ogr doesn't like unicode.
    elif layername is not None:  #then a layername
        layer=ds.GetLayerByName(layername)
    else: #fallback - shapefiles etc, use first layer
        layer=ds.GetLayer(0)
    assert(layer is not None)
    return ds,layer

def nptype2gdal(dtype):
    if dtype==np.float32:
        return gdal.GDT_Float32
    elif dtype==np.float64:
        return gdal.GDT_Float64
    elif dtype==np.int32:
        return gdal.GDT_Int32
    elif dtype==np.bool or dtype==np.uint8:
        return gdal.GDT_Byte
    return gdal.GDT_Float64	
    

def burn_vector_layer(cstr,georef,shape,layername=None,layersql=None,attr=None,nd_val=0,dtype=np.bool,all_touched=True):
    #For now just burn a mask - can be expanded to burn attrs. by adding keywords.
    #input a GDAL-style georef
    #If executing fancy sql like selecting buffers etc, be sure to add a where ST_Intersects(geom,TILE_POLY) - otherwise its gonna be slow....
    extent=(georef[0],georef[3]+shape[1]*georef[5],georef[0]+shape[0]*georef[1],georef[3]) #x1,y1,x2,y2
    ds,layer=open(cstr,layername,layersql,extent)
    #This should do nothing if already filtered in sql...
    layer.SetSpatialFilterRect(*extent)
    mem_driver=gdal.GetDriverByName("MEM")
    gdal_type=nptype2gdal(dtype)
    mask_ds=mem_driver.Create("dummy",int(shape[1]),int(shape[0]),1,gdal_type)
    mask_ds.SetGeoTransform(georef)
    mask=np.ones(shape,dtype=dtype)*nd_val
    mask_ds.GetRasterBand(1).WriteArray(mask) #write nd_val to output
    #mask_ds.SetProjection('LOCAL_CS["arbitrary"]')
    if all_touched:
        options=['ALL_TOUCHED=TRUE']
    else:
        options=[]
    if attr is not None: #we want to burn an attribute - take a different path
        options.append('ATTRIBUTE=%s'%attr)
        ok=gdal.RasterizeLayer(mask_ds,[1],layer, options=options)
    else:
        ok=gdal.RasterizeLayer(mask_ds,[1],layer,burn_values=[1],options=options)
    A=mask_ds.ReadAsArray().astype(dtype)
    if layersql is not None:
        ds.ReleaseResultSet(layer)
    layer=None
    ds=None
    return A

def get_geometries(cstr, layername=None, layersql=None, extent=None, explode=True):
    #If executing fancy sql like selecting buffers etc, be sure to add a where ST_Intersects(geom,TILE_POLY) - otherwise its gonna be slow....
    t1=time.clock()
    ds,layer=open(cstr,layername,layersql,extent)
    if extent is not None:
        layer.SetSpatialFilterRect(*extent)
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
            if (t!=ogr.wkbPolygon and t!=ogr.wkbPolygon25D) and (explode):
                #so must be a multi-geometry - explode it
                geoms_here=[geom.GetGeometryRef(i).Clone() for i in range(ng)]
        geoms.extend(geoms_here)

    if layersql is not None:
        ds.ReleaseResultSet(layer)
    layer=None
    ds=None
    t2=time.clock()
    print("Fetching geoms took %.3f s" %(t2-t1))
    return geoms

def get_features(cstr, layername=None, layersql=None, extent=None):
    ds,layer=open(cstr,layername,layersql,extent)
    if extent is not None:
        layer.SetSpatialFilterRect(*extent)
    feats=[f for f in layer]
    if layersql is not None:
        ds.ReleaseResultSet(layer)
    layer=None
    ds=None
    return feats
    
def polygonize(M,georef):
    #polygonize an input Mask (bool or uint8 -todo, add more types)
    dst_fieldname='DN'
    #create a GDAL memory raster
    mem_driver=gdal.GetDriverByName("MEM")
    mask_ds=mem_driver.Create("dummy",int(M.shape[1]),int(M.shape[0]),1,gdal.GDT_Byte)
    mask_ds.SetGeoTransform(georef)
    mask_ds.GetRasterBand(1).WriteArray(M) #write zeros to output
    #Ok - so now polygonize that - use the mask as ehem... mask...
    m_drv=ogr.GetDriverByName("Memory")
    ds = m_drv.CreateDataSource( "dummy")
    lyr = ds.CreateLayer( "polys", None, ogr.wkbPolygon)
    fd = ogr.FieldDefn( dst_fieldname, ogr.OFTInteger )
    lyr.CreateField( fd )
    dst_field = 0
    gdal.Polygonize(mask_ds.GetRasterBand(1), mask_ds.GetRasterBand(1), lyr, dst_field)
    lyr.ResetReading()
    return ds, lyr

    