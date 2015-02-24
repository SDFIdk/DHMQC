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
###############################################
## Result storing module            
## Uses ogr simple feature model to store results in e.g. a database
###############################################
import os
from osgeo import ogr, osr
from dhmqc_constants import PG_CONNECTION, EPSG_CODE
import datetime
if PG_CONNECTION is not None and not PG_CONNECTION.startswith("PG:"):
	PG_CONNECTION="PG: "+PG_CONNECTION
USE_LOCAL=False #global flag which can override parameter in call to get_output_datasource
DATA_SOURCE=None #we can keep a reference to an open datasource here - can be set pr. process with set_datasource
FALL_BACK="./dhmqc.sqlite" #hmm - we should use some kind of fall-back ds, e.g. if we're offline
FALL_BACK_FRMT="SQLITE"
FALL_BACK_DSCO=["SPATIALITE=YES"]

#The default schema - default table names should start with this... will be replaced if SCHEMA is not None


RUN_ID=None   # A global id, which can be set from a wrapper script pr. process
SCHEMA_NAME=None


def set_run_id(id):
	global RUN_ID
	RUN_ID=int(id)

def set_schema(name):
	global SCHEMA_NAME
	SCHEMA_NAME=name
	#Her gaar der lidt ged i det og bliver uskoent - Simon skal vist se lidt paa arkitekturen i det her	

class LayerDefinition(object):
	def __init__(self,name,geometry_type,field_list):
		self.name=name
		self.geometry_type=geometry_type
		self.field_list=field_list


#LAYER_DEFINITIONS
#DETERMINES THE ORDERING AND THE TYPE OF THE ARGUMENTS TO THE report METHOD !!!!		
LAYERS={		
"Z_CHECK_ROAD": LayerDefinition("f_z_precision_roads",ogr.wkbLineString25D,
			(("km_name",ogr.OFTString),
			("id1",ogr.OFTInteger),
			("id2",ogr.OFTInteger),
			("mean12",ogr.OFTReal),
			("mean21",ogr.OFTReal),
			("sigma12",ogr.OFTReal),
			("sigma21",ogr.OFTReal),
			("rms12",ogr.OFTReal),
			("rms21",ogr.OFTReal),
			("npoints12",ogr.OFTInteger),
			("npoints21",ogr.OFTInteger),
			("combined_precision",ogr.OFTReal),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),

"Z_CHECK_BUILD":LayerDefinition("f_z_precision_buildings",ogr.wkbPolygon25D,
			(("km_name",ogr.OFTString),
			("id1",ogr.OFTInteger),
			("id2",ogr.OFTInteger),
			("mean12",ogr.OFTReal),
			("mean21",ogr.OFTReal),
			("sigma12",ogr.OFTReal),
			("sigma21",ogr.OFTReal),
			("rms12",ogr.OFTReal),
			("rms21",ogr.OFTReal),
			("npoints12",ogr.OFTInteger),
			("npoints21",ogr.OFTInteger),
			("combined_precision",ogr.OFTReal),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),

"Z_CHECK_ABS":LayerDefinition("f_z_accuracy",ogr.wkbPoint25D,
		(("km_name",ogr.OFTString),
		("id",ogr.OFTInteger),("f_type",ogr.OFTString),
		("mean",ogr.OFTReal),
		("sigma",ogr.OFTReal),
		("npoints",ogr.OFTInteger),
		("run_id",ogr.OFTInteger),
		("ogr_t_stamp",ogr.OFTDateTime))),

"Z_CHECK_GCP": LayerDefinition("f_z_accuracy_gcp",ogr.wkbPoint25D,
		(("km_name",ogr.OFTString),
		("z",ogr.OFTReal),
		("dz",ogr.OFTReal),
		("t_angle",ogr.OFTReal),
		("t_size",ogr.OFTReal),
		("run_id",ogr.OFTInteger))),

"DENSITY":LayerDefinition("f_point_density",ogr.wkbPolygon,
		(("km_name",ogr.OFTString),
		("min_point_density",ogr.OFTReal),
		("mean_point_density",ogr.OFTReal),
		("cell_size",ogr.OFTReal),
		("run_id",ogr.OFTInteger),
		("ogr_t_stamp",ogr.OFTDateTime))),

#the ordering of classes here should be numeric as in dhmqc_constants - to not mix up classes!
"CLASS_CHECK":LayerDefinition("f_classification",ogr.wkbPolygon,
			(("km_name",ogr.OFTString),
			("f_created_00",ogr.OFTReal),
			("f_surface_1",ogr.OFTReal),
			("f_terrain_2",ogr.OFTReal),
			("f_low_veg_3",ogr.OFTReal),
			("f_med_veg_4",ogr.OFTReal),
			("f_high_veg_5",ogr.OFTReal),
			("f_building_6",ogr.OFTReal),
			("f_outliers_7",ogr.OFTReal),
			("f_mod_key_8",ogr.OFTReal),
			("f_water_9",ogr.OFTReal),
			("f_ignored_10",ogr.OFTReal),
			("f_bridge_17",ogr.OFTReal),
			("f_man_excl_32",ogr.OFTReal),
			("f_other",ogr.OFTReal),
			("n_points_total",ogr.OFTInteger),
			("ptype",ogr.OFTString),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),
			
"CLASS_COUNT":LayerDefinition("f_classes_in_tiles",ogr.wkbPolygon,
			 (("km_name",ogr.OFTString),
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
			 ("n_points_total",ogr.OFTInteger),
			 ("run_id",ogr.OFTInteger),
			 ("ogr_t_stamp",ogr.OFTDateTime))),

"ROOFRIDGE_ALIGNMENT":LayerDefinition("f_roof_ridge_alignment",ogr.wkbLineString25D,
			(("km_name",ogr.OFTString),
			("rotation",ogr.OFTReal),
			("dist1",ogr.OFTReal),
			("dist2",ogr.OFTReal),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),

"ROOFRIDGE_STRIPS":LayerDefinition("f_roof_ridge_strips",ogr.wkbLineString25D,
			(("km_name",ogr.OFTString),
			("id1",ogr.OFTString),
			("id2",ogr.OFTString),
			("stripids",ogr.OFTString),
			("pair_dist",ogr.OFTReal),
			("pair_rot",ogr.OFTReal),
			("z",ogr.OFTReal),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),
			
"BUILDING_ABSPOS":LayerDefinition("f_xy_accuracy_buildings",ogr.wkbPolygon25D,
			(("km_name",ogr.OFTString),
			("scale",ogr.OFTReal),
			("dx",ogr.OFTReal),
			("dy",ogr.OFTReal),
			("n_points",ogr.OFTInteger),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),
			
"BUILDING_RELPOS":LayerDefinition("f_xy_precision_buildings",ogr.wkbPolygon25D,
			(("km_name",ogr.OFTString),
			("id1",ogr.OFTString),
			("id2",ogr.OFTString),
			("dx",ogr.OFTReal),
			("dy",ogr.OFTReal),
			("dist",ogr.OFTReal),
			("h_scale",ogr.OFTReal),
			("h_dx",ogr.OFTReal),
			("h_dy",ogr.OFTReal),
			("h_sdx",ogr.OFTReal),
			("h_sdy",ogr.OFTReal),
			("n_points",ogr.OFTInteger),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),

"AUTO_BUILDING":LayerDefinition("f_auto_building",ogr.wkbPolygon,
			(("km_name",ogr.OFTString),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),
				 
"CLOUDS":LayerDefinition("f_clouds",ogr.wkbPolygon,
			(("km_name",ogr.OFTString),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),
			

"DELTA_ROADS":LayerDefinition("f_delta_roads",ogr.wkbMultiPoint,
			(("km_name",ogr.OFTString),
			("z_step_max",ogr.OFTReal),
			("z_step_min",ogr.OFTReal),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),

"SPIKES":LayerDefinition("f_spikes",ogr.wkbPoint,
			(("km_name",ogr.OFTString),
			("filter_rad",ogr.OFTReal),
			("mean_dz",ogr.OFTReal),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),

"STEEP_TRIANGLES":LayerDefinition("f_steep_triangles",ogr.wkbPoint,
			(("km_name",ogr.OFTString),
			("class",ogr.OFTInteger),
			("slope",ogr.OFTReal),
			("xybox",ogr.OFTReal),
			("zbox",ogr.OFTReal),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime))),

"WOBBLY_WATER":LayerDefinition("f_wobbly_water",ogr.wkbPolygon,
			(("km_name",ogr.OFTString),
			("class",ogr.OFTInteger),
			("frad",ogr.OFTReal),
			("npoints",ogr.OFTReal),
			("min_diff",ogr.OFTReal),
			("max_diff",ogr.OFTReal),
			("run_id",ogr.OFTInteger),
			("ogr_t_stamp",ogr.OFTDateTime)))
}
				 




	
	
def create_local_datasource(name=None,overwrite=False):
	if name is None:
		name=FALL_BACK
	drv=ogr.GetDriverByName(FALL_BACK_FRMT)
	if overwrite: 
		drv.DeleteDataSource(name)
		ds=None
	else:
		ds=ogr.Open(name,True)
	SRS=osr.SpatialReference()
	SRS.ImportFromEPSG(EPSG_CODE)
	if ds is None:
		print("Creating local data source for reporting.")
		ds=drv.CreateDataSource(name,FALL_BACK_DSCO)
	for key in LAYERS:
		defn=LAYERS[key]
		name=defn.name
		layer=ds.GetLayerByName(name)
		if layer is None:
			print("Creating: "+name)
			layer=ds.CreateLayer(name,SRS,defn.geometry_type)
			for field_name,field_type in defn.field_list:
				field_defn = ogr.FieldDefn(field_name, field_type)
				if field_type==ogr.OFTString:
					field_defn.SetWidth( 32 )
				ok=layer.CreateField(field_defn)
				assert(ok==0)
	return ds

def schema_exists(schema):
	assert (PG_CONNECTION is not None)
	test_connection=PG_CONNECTION+" active_schema="+schema
	ds=ogr.Open(test_connection)
	schema_ok=ds is not None
	layers_ok=True
	if ds is not None:
		for key in LAYERS:
			defn=LAYERS[key]
			layer=ds.GetLayerByName(defn.name)
			if layer is None:
				layers_ok=False
				break
	ds=None
	return schema_ok,layers_ok
	

def create_schema(schema, overwrite=False): #overwrite will eventually be used to force deletion of existing layers...
	if PG_CONNECTION is None:
		raise ValueError("Define PG_CONNECTION in pg_connection.py")
	#Test if schema already exists!
	schema_ok,layers_ok=schema_exists(schema)
	if schema_ok and layers_ok:
		return
	ds=ogr.Open(PG_CONNECTION,True)
	if ds is None:
		raise ValueError("Failed to open: "+PG_CONNECTION)
	SRS=osr.SpatialReference()
	SRS.ImportFromEPSG(EPSG_CODE)
	print("Creating schema "+schema+" in global data source for reporting.")
	#active schema will be public unless
	if not schema_ok:
		ok=ds.ExecuteSQL("CREATE SCHEMA "+schema)
	for key in LAYERS:
		defn=LAYERS[key]
		name=schema+"."+defn.name
		layer=ds.GetLayerByName(name)
		if layer is None:
			print("Creating: "+name)
			layer=ds.CreateLayer(name,SRS,defn.geometry_type)
			for field_name,field_type in defn.field_list:
				field_defn = ogr.FieldDefn(field_name, field_type)
				if field_type==ogr.OFTString:
					field_defn.SetWidth( 32 )
				ok=layer.CreateField(field_defn)
				assert(ok==0)
	ds=None
	

def set_use_local(use_local):
	#force using a local db - no matter what...
	global USE_LOCAL
	USE_LOCAL=use_local
	
def set_datasource(ds):
	#Force using this datasource pr. process
	global DATA_SOURCE
	DATA_SOURCE=ds

def get_output_datasource(use_local=False):
	#The global USE_LOCAL will override the given argument.
	if DATA_SOURCE is not None:
		return DATA_SOURCE
	ds=None
	if not (use_local or USE_LOCAL):
		if PG_CONNECTION is None:
			raise ValueError("PG_CONNECTION to global db is not defined")
		ds=ogr.Open(PG_CONNECTION,True)
	else: #less surprising behaviour rather than suddenly falling back on a local ds...
		ds=ogr.Open(FALL_BACK,True)
	return ds


#Base reporting class	
class ReportBase(object):
	LAYER_DEFINITION=None
	def __init__(self,use_local,run_id=None):
		self.layername = self.LAYER_DEFINITION.name
		if DATA_SOURCE is not None:
			print("Using open data source for reporting.")
		else:
			if use_local or USE_LOCAL:
				print("Using local data source for reporting.")
			else:
				print("Using global data source for reporting.")
				if SCHEMA_NAME is not None:
					print("Schema is "+SCHEMA_NAME)
					self.layername = SCHEMA_NAME+"."+self.layername
		self.ds=get_output_datasource(use_local)
		if self.ds is not None:
			self.layer=self.ds.GetLayerByName(self.layername)
			self.layerdefn=self.layer.GetLayerDefn()
		else:
			raise Warning("Failed to open data source- you might need to CREATE one...")
			self.layer=None
		if self.layer is None:
			raise Warning("Layer "+self.layername+" could not be opened. Nothing will be reported.")
		if run_id is None: #if not specified, use the global one, which might be set from a wrapper...
			run_id=RUN_ID 
		self.run_id=run_id
		print("Run id is: %s" %self.run_id)
	def _report(self,*args,**kwargs):
		if self.layer is None:
			return 1
		feature=ogr.Feature(self.layer.GetLayerDefn())
		for i,arg in enumerate(args):
			if arg is not None:
				defn=self.LAYER_DEFINITION.field_list[i]
				if defn[1]==ogr.OFTString:
					val=str(arg)
				elif defn[1]==ogr.OFTInteger:
					val=int(arg)
				elif defn[1]==ogr.OFTReal:
					val=float(arg)
				else: #unsupported data type
					pass
				feature.SetField(defn[0],val)
		if self.run_id is not None:
			feature.SetField("run_id",self.run_id)
		if self.layerdefn.GetFieldIndex("ogr_t_stamp")>0:
			d=datetime.datetime.now()
			feature.SetField("ogr_t_stamp",d.year,d.month,d.day,d.hour,d.minute,d.second,1)
		#geom given by keyword wkt_geom or ogr_geom, we do not seem to need wkb_geom...
		geom=None
		if "ogr_geom" in kwargs:
			geom=kwargs["ogr_geom"]
		elif "wkt_geom" in kwargs:
			geom=ogr.CreateGeometryFromWkt(kwargs["wkt_geom"])
		if geom is not None:
			feature.SetGeometry(geom)
		
		res=self.layer.CreateFeature(feature)
		return res
	#args must come in the order defined by layer definition above, geom given in kwargs as ogr_geom og wkt_geom
	def report(self,*args,**kwargs):
		#Method to override for subclasses...
		return self._report(*args,**kwargs)

class ReportClassCheck(ReportBase):
	LAYER_DEFINITION=LAYERS["CLASS_CHECK"]

class ReportClassCount(ReportBase):
	LAYER_DEFINITION=LAYERS["CLASS_COUNT"]

class ReportZcheckAbs(ReportBase):
	LAYER_DEFINITION=LAYERS["Z_CHECK_ABS"]

class ReportZcheckAbsGCP(ReportBase):
	LAYER_DEFINITION=LAYERS["Z_CHECK_GCP"]
	
class ReportRoofridgeCheck(ReportBase):
	LAYER_DEFINITION=LAYERS["ROOFRIDGE_ALIGNMENT"]

class ReportRoofridgeStripCheck(ReportBase):
	LAYER_DEFINITION=LAYERS["ROOFRIDGE_STRIPS"]

class ReportBuildingAbsposCheck(ReportBase):
	LAYER_DEFINITION=LAYERS["BUILDING_ABSPOS"]
	
class ReportBuildingRelposCheck(ReportBase):
	LAYER_DEFINITION=LAYERS["BUILDING_RELPOS"]

class ReportDensity(ReportBase):
	LAYER_DEFINITION=LAYERS["DENSITY"]

class ReportZcheckRoad(ReportBase):
	LAYER_DEFINITION=LAYERS["Z_CHECK_ROAD"]

class ReportZcheckBuilding(ReportBase):
	LAYER_DEFINITION=LAYERS["Z_CHECK_BUILD"]

class ReportAutoBuilding(ReportBase):
	LAYER_DEFINITION=LAYERS["AUTO_BUILDING"]
	
class ReportClouds(ReportBase):
	LAYER_DEFINITION=LAYERS["CLOUDS"]

class ReportDeltaRoads(ReportBase):
	LAYER_DEFINITION=LAYERS["DELTA_ROADS"]

class ReportSpikes(ReportBase):
	LAYER_DEFINITION=LAYERS["SPIKES"]

class ReportSteepTriangles(ReportBase):
	LAYER_DEFINITION=LAYERS["STEEP_TRIANGLES"]

class ReportWobbly(ReportBase):
	LAYER_DEFINITION=LAYERS["WOBBLY_WATER"]
	










	

	
	