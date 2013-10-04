###############################################
## Result storing module            
## Uses ogr simple feature model to store results in e.g. a database
###############################################
from osgeo import ogr
PG_CONNECTION="PG: host=sit1200038.RES.Adroot.dk port=5432 dbname=dhmqc user=postgres password=postgres"
FALL_BACK="./dhmqc.sqlite" #hmm - we should use some kind of fall-back ds, e.g. if we're offline
Z_CHECK_TABLE="dhmqc.zcheck"
#TODO:  layer definition for fallback   Z_CHECK_TABLE_DEFN={"kmname":"kmname","mean":"mean_err","

def create_local_datasource():
	#TODO: create a local sqlite db or something, with similar structure as the PG-db, to be used as a fall-back
	pass


def get_output_datasource():
	ds=ogr.Open(PG_CONNECTION,True)
	if ds is None:
		#TODO: use fallback here#
		raise Exception("Failed to open Postgis connection")
	return ds



#And it works!
def report_zcheck(km_name,strip_id1,strip_id2,mean_val,sigma_naught,wkb_geom=None,wkt_geom=None,ogr_geom=None,comment=None):
	ds=get_output_datasource()
	layer=ds.GetLayerByName(Z_CHECK_TABLE)
	if layer is None:
		#TODO: some kind of fallback here - instead of letting calculations stop#
		raise Exception("Failed to fetch zcheck layer")
	#print km_name,strip_id1,strip_id2,mean_val,sigma_naught
	#return True
	feature=ogr.Feature(layer.GetLayerDefn())
	#The following should match the layer definition!
	feature.SetField("km_name",km_name)
	feature.SetField("id1",int(strip_id1))
	feature.SetField("id2",int(strip_id2))
	feature.SetField("mean_val",float(mean_val))
	feature.SetField("sigma_naught",float(sigma_naught))
	geom=None
	if ogr_geom is not None and isinstance(ogr_geom,ogr.Geometry):
		geom=ogr_geom
	elif (wkb_geom is not None):
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

