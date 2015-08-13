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

EXTENT_WKT="WKT_EXT" #placeholder for tile-wkt - thos token will be replaced by actual wkt in run time.


def open(cstr,layername=None,layersql=None,extent=None):
    """
    Common opener of an OGR datasource. Use either layername or layersql.
    Will directly modify layersql to make the data provider do the filtering by extent if using the WKT_EXT token.
    Returns:
        OGR datasource ,  OGR layer
    """
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
    """
    Translate a numpy datatype to a corresponding GDAL datatype (similar to mappings internal in GDAL/OGR)
    Arg:
        A numpy datatype
    Returns:
        A GDAL datatype (just a member of an enumeration)
    """
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
    """
    Burn a vector layer. Will use vector_io.open to fetch the layer.
    Returns:
        A numpy array of the requested dtype and shape.
    """
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

def just_burn_layer(layer,georef,shape,attr=None,nd_val=0,dtype=np.bool,all_touched=True,burn3d=False):
    """
    Burn a vector layer. Similar to vector_io.burn_vector_layer except that the layer is given directly in args.
    Returns:
        A numpy array of the requested dtype and shape.
    """
    if burn3d and attr is not None:
        raise ValueError("burn3d and attr can not both be set")
    extent=(georef[0],georef[3]+shape[1]*georef[5],georef[0]+shape[0]*georef[1],georef[3]) #x1,y1,x2,y2
    layer.SetSpatialFilterRect(*extent)
    mem_driver=gdal.GetDriverByName("MEM")
    gdal_type=nptype2gdal(dtype)
    mask_ds=mem_driver.Create("dummy",int(shape[1]),int(shape[0]),1,gdal_type)
    mask_ds.SetGeoTransform(georef)
    mask=np.ones(shape,dtype=dtype)*nd_val
    mask_ds.GetRasterBand(1).WriteArray(mask) #write nd_val to output
    #mask_ds.SetProjection('LOCAL_CS["arbitrary"]')
    options=[]
    if all_touched:
        options.append('ALL_TOUCHED=TRUE')
    if attr is not None: #we want to burn an attribute - take a different path
        options.append('ATTRIBUTE=%s'%attr)
    if burn3d:
        options.append('BURN_VALUE_FROM=Z')
    if attr is not None:
        ok=gdal.RasterizeLayer(mask_ds,[1], layer, options=options)
    else:
        if burn3d:
            burn_val=0  # as explained by Even Rouault default burn val is 255 if not given. So for burn3d we MUST supply burnval=0 and 3d part will be added to that.
        else:
            burn_val=1
        ok=gdal.RasterizeLayer(mask_ds,[1],layer,burn_values=[burn_val],options=options)
    A=mask_ds.ReadAsArray().astype(dtype)
    return A

def get_geometries(cstr, layername=None, layersql=None, extent=None, explode=True):
    """
    Use vector_io.open to fetch a layer, read geometries and explode multi-geometries if explode=True
    Returns:
        A list of OGR geometries.
    """
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
    """
    Use vector_io.open to fetch a layer and read all features.
    Returns:
        A list of OGR features.
    """
    
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
    """
    Polygonize a mask.
    Args:
        M: a numpy 'mask' array.
        georef: GDAL style georeference of mask.
    Returns:
        OGR datasource, OGR layer
    """
    #TODO: supply srs 
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

    