###############################################
## Result storing module            
## Uses ogr simple feature model to store results in e.g. a database
###############################################
import os
from osgeo import ogr
USE_LOCAL=False #global flag which can override parameter in call to get_output_datasource
PG_CONNECTION="PG: host=sit1200038.RES.Adroot.dk port=5432 dbname=dhmqc user=postgres password=postgres"
FALL_BACK="./dhmqc.sqlite" #hmm - we should use some kind of fall-back ds, e.g. if we're offline
FALL_BACK_FRMT="SQLITE"
FALL_BACK_DSCO=["SPATIALITE=YES"]
Z_CHECK_ROAD_TABLE="dhmqc.f_zcheck_roads"
Z_CHECK_BUILD_TABLE="dhmqc.f_zcheck_buildings"
C_CHECK_TABLE="dhmqc.f_classicheck"
C_COUNT_TABLE="dhmqc.f_classes_in_tiles"
#LAYER_DEFINITIONS
Z_CHECK_ROAD_DEF=[("km_name",ogr.OFTString),("id1",ogr.OFTInteger),("id2",ogr.OFTInteger),
("mean12",ogr.OFTReal),("sigma12",ogr.OFTReal),("npoints12",ogr.OFTInteger),
("mean21",ogr.OFTReal),("sigma21",ogr.OFTReal),("npoints21",ogr.OFTInteger),("combined_precision",ogr.OFTReal)]
Z_CHECK_BUILD_DEF=Z_CHECK_ROAD_DEF
C_CHECK_DEF=[("km_name",ogr.OFTString),("c_class",ogr.OFTInteger),("c_frequency",ogr.OFTReal),("npoints",ogr.OFTInteger)]

C_COUNT_DEF=[("km_name",ogr.OFTString),
			 ("n_created_00",ogr.OFTInteger),
			 ("n_surface_1",ogr.OFTInteger),
			 ("n_terrain_2",ogr.OFTInteger),
			 ("n_low_veg_3",ogr.OFTInteger),
			 ("n_med_veg_4",ogr.OFTInteger),
			 ("n_high_veg_5",ogr.OFTInteger),
			 ("n_building_6",ogr.OFTInteger),
			 ("n_outliers_7",ogr.OFTInteger),
			 ("n_mod_key_8",ogr.OFTInteger),
			 ("n_water_9",ogr.OFTInteger),
			 ("n_ignored_10",ogr.OFTInteger),
			 ("n_bridge_17",ogr.OFTInteger),
			 ("n_man_excl_32",ogr.OFTInteger),
			 ("n_points_total",ogr.OFTInteger)]

LAYERS={Z_CHECK_ROAD_TABLE:[ogr.wkbLineString,Z_CHECK_ROAD_DEF],Z_CHECK_BUILD_TABLE:[ogr.wkbPolygon,Z_CHECK_BUILD_DEF],
C_CHECK_TABLE:[ogr.wkbPolygon,C_CHECK_DEF],C_COUNT_TABLE:[ogr.wkbPolygon,C_COUNT_DEF]}

def create_local_datasource():
	ds=ogr.Open(FALL_BACK,True)
	if ds is None:
		print("Creating local data source for reporting.")
		drv=ogr.GetDriverByName(FALL_BACK_FRMT)
		ds=drv.CreateDataSource(FALL_BACK,FALL_BACK_DSCO)
		for layer_name in LAYERS:
			geom_type,layer_def=LAYERS[layer_name]
			layer=ds.CreateLayer(layer_name,None,geom_type)
			for field_name,field_type in layer_def:
				field_defn = ogr.FieldDefn(field_name, field_type)
				if field_type==ogr.OFTString:
					field_defn.SetWidth( 32 )
				ok=layer.CreateField(field_defn)
	return ds
	

def set_use_local(use_local):
	global USE_LOCAL
	USE_LOCAL=use_local

def get_output_datasource(use_local=False):
	ds=None
	if not (use_local or USE_LOCAL):
		ds=ogr.Open(PG_CONNECTION,True)
	if ds is None:
		ds=ogr.Open(FALL_BACK,True)
	return ds

#stats is a list of [mean,sd,npoints]
def report_zcheck(ds,km_name,strip_id1,strip_id2,c_prec,stats12=None,stats21=None,wkb_geom=None,wkt_geom=None,ogr_geom=None,use_local=False, table=Z_CHECK_ROAD_TABLE):
	layer=ds.GetLayerByName(table)
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
	if stats12 is not None:
		feature.SetField("mean12",float(stats12[0]))
		feature.SetField("sigma12",float(stats12[1]))
		feature.SetField("npoints12",int(stats12[2]))
	if stats21 is not None:
		feature.SetField("mean21",float(stats21[0]))
		feature.SetField("sigma21",float(stats21[1]))
		feature.SetField("npoints21",int(stats21[2]))
	feature.SetField("combined_precision",float(c_prec))
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

def report_zcheck_road(*args,**kwargs):
	kwargs["table"]=Z_CHECK_ROAD_TABLE
	return report_zcheck(*args,**kwargs)

def report_zcheck_building(*args,**kwargs):
	kwargs["table"]=Z_CHECK_BUILD_TABLE
	return report_zcheck(*args,**kwargs)

def report_class_check(ds,km_name,c_checked,f_good,n_all,wkb_geom=None,wkt_geom=None,ogr_geom=None,use_local=False):
	layer=ds.GetLayerByName(C_CHECK_TABLE)
	if layer is None:
		#TODO: some kind of fallback here - instead of letting calculations stop#
		raise Exception("Failed to fetch classification check layer")
	#print km_name,strip_id1,strip_id2,mean_val,sigma_naught
	#return True
	feature=ogr.Feature(layer.GetLayerDefn())
	#The following should match the layer definition!
	feature.SetField("km_name",str(km_name))
	feature.SetField("c_class",int(c_checked))
	feature.SetField("c_frequency",float(f_good))
	feature.SetField("npoints",int(n_all))
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

def report_class_count(ds,km_name,n_created_unused,n_surface,n_terrain,n_low_veg,n_med_veg,n_high_veg,n_building,n_outliers,n_mod_key,n_water,n_ignored,n_bridge,n_man_excl,n_points_total,wkb_geom=None,wkt_geom=None,ogr_geom=None,use_local=False):
	layer=ds.GetLayerByName(C_COUNT_TABLE)
	if layer is None:
		#TODO: some kind of fallback here - instead of letting calculations stop#
		raise Exception("Failed to fetch classification count layer")
	feature=ogr.Feature(layer.GetLayerDefn())
	#The following should match the layer definition!
	feature.SetField("km_name",str(km_name))
	feature.SetField("n_created_00",int(n_created_unused))	
	feature.SetField("n_surface_1",int(n_surface))	
	feature.SetField("n_terrain_2",int(n_terrain))	
	feature.SetField("n_low_veg_3",int(n_low_veg))	
	feature.SetField("n_med_veg_4",int(n_med_veg))	
	feature.SetField("n_high_veg_5",int(n_high_veg))	
	feature.SetField("n_building_6",int(n_building))
	feature.SetField("n_outliers_7",int(n_outliers))
	feature.SetField("n_mod_key_8",int(n_mod_key))
	feature.SetField("n_water_9",int(n_water))
	feature.SetField("n_ignored_10",int(n_ignored))
	feature.SetField("n_bridge_17",int(n_bridge))
	feature.SetField("n_man_excl_32",int(n_man_excl))
	feature.SetField("n_points_total",int(n_points_total))
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

	
	