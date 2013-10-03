###############################################
## Result storing module            
## Uses ogr simple feature model to store results in e.g. a database
###############################################
from osgeo import ogr
PG_CONNECTION="PG: host=sit1200038.RES.Adroot.dk port=5432 dbname=dhmqc user=postgres password=postgres"
FALL_BACK="./dhmqc.sqlite" #hmm - we should use some kind of fall-back ds, e.g. if we're offline
Z_CHECK_TABLE="dhmqc.zcheck"
#TODO:  layer definition for fallback   Z_CHECK_TABLE_DEFN={"kmname":"kmname","mean":"mean_err","

def report_zcheck(km_name,strip_id1,strip_id2,mean_val,sigma_naught,wkb_geom=None,wkt_geom=None,comment=None):
	ds=ogr.Open(PG_CONNECTION)
	if ds is None:
		#TODO: use fallback here#
		#possibly also create the output layer...#
		raise Exception("Failed to open Postgis connection")
	else:
		layer=ds.GetLayerByName(Z_CHECK_TABLE)
	if layer is None:
		#TODO: some kind of fallback here#
		raise Exception("Failed to fetch zcheck layer")
	feature=ogr.Feature(layer.GetLayerDefn())
	#The following should match the layer definition!
	feature.SetField("km_name",kmname)
	feature.SetField("id1",strip_id1)
	feature.SetField("id2",strip_id2)
	feature.SetField("mean_val",mean_val)
	feature.SetField("sigma_naught",sigma_naught)
	geom=None
	if (wkb_geom is not None):
		geom=ogr.CreateGeometryFromWkb(wkb_geom)
	elif (wkt_geom is not None):
		geom=ogr.CreateGeometryFromWkt(wkt_geom)
	if geom is not None:
		feature.SetGeometry(geom)
	res=layer.CreateFeature(feature)
	layer=None
	ds=None #garbage collector will close the datasource....
	if res!=0:
		return False
	return True

