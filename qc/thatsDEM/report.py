###############################################
## Result storing module            
## Uses ogr simple feature model to store results in e.g. a database
###############################################
import os
from osgeo import ogr
from dhmqc_constants import PG_CONNECTION
USE_LOCAL=False #global flag which can override parameter in call to get_output_datasource
#PG_CONNECTION="PG: host=C1200038 port=5432 dbname=dhmqc user=postgres password=postgres"
FALL_BACK="./dhmqc.sqlite" #hmm - we should use some kind of fall-back ds, e.g. if we're offline
FALL_BACK_FRMT="SQLITE"
FALL_BACK_DSCO=["SPATIALITE=YES"]


Z_CHECK_ROAD_TABLE="dhmqc.f_z_precision_roads"
Z_CHECK_BUILD_TABLE="dhmqc.f_z_precision_buildings"
Z_CHECK_ABS_TABLE="dhmqc.f_z_accuracy"
C_CHECK_TABLE="dhmqc.f_classification"
C_COUNT_TABLE="dhmqc.f_classes_in_tiles"
R_ROOFRIDGE_TABLE="dhmqc.f_roof_ridge_alignment"
R_ROOFRIDGE_STRIPS_TABLE="dhmqc.f_roof_ridge_strips"
R_BUILDING_ABSPOS_TABLE="dhmqc.f_xy_accuracy_buildings"
R_BUILDING_RELPOS_TABLE="dhmqc.f_xy_precision_buildings"
B_AUTO_BUILDING_TABLE="dhmqc.f_auto_building"
B_CLOUDS_TABLE="dhmqc.f_clouds"
D_DENSITY_TABLE="dhmqc.f_point_density"
D_DELTA_ROADS_TABLE="dhmqc.f_delta_roads"

#LAYER_DEFINITIONS
#DETERMINES THE ORDERING AND THE TYPE OF THE ARGUMENTS TO THE report METHOD !!!!
Z_CHECK_ROAD_DEF=[("km_name",ogr.OFTString),
			("id1",ogr.OFTInteger),("id2",ogr.OFTInteger),
			("mean12",ogr.OFTReal),("mean21",ogr.OFTReal),
			("sigma12",ogr.OFTReal),("sigma21",ogr.OFTReal),
			("rms12",ogr.OFTReal),("rms21",ogr.OFTReal),
			("npoints12",ogr.OFTInteger),("npoints21",ogr.OFTInteger),
			("combined_precision",ogr.OFTReal),("run_id",ogr.OFTInteger)]

Z_CHECK_BUILD_DEF=Z_CHECK_ROAD_DEF
Z_CHECK_ABS_DEF=[("km_name",ogr.OFTString),("id",ogr.OFTInteger),("f_type",ogr.OFTString),
("mean",ogr.OFTReal),("sigma",ogr.OFTReal),("npoints",ogr.OFTInteger),("run_id",ogr.OFTInteger)]

D_DENSITY_DEF=[("km_name",ogr.OFTString),("min_point_density",ogr.OFTReal),("mean_point_density",ogr.OFTReal),("cell_size",ogr.OFTReal),("run_id",ogr.OFTInteger)]

#the ordering of classes here should be numeric as in dhmqc_constants - to not mix up classes!
C_CHECK_DEF=[("km_name",ogr.OFTString),
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
			("run_id",ogr.OFTInteger)]
			

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
			 ("n_points_total",ogr.OFTInteger),
			 ("run_id",ogr.OFTInteger)]

R_ROOFRIDGE_DEF=[("km_name",ogr.OFTString),
			 ("rotation",ogr.OFTReal),
			 ("dist1",ogr.OFTReal),
			 ("dist2",ogr.OFTReal),
			 ("run_id",ogr.OFTInteger)]

R_ROOFRIDGE_STRIPS_DEF=[("km_name",ogr.OFTString),
			 ("id1",ogr.OFTString),
			 ("id2",ogr.OFTString),
			 ("stripids",ogr.OFTString),
			 ("pair_dist",ogr.OFTReal),
			 ("pair_rot",ogr.OFTReal),
			 ("z",ogr.OFTReal),
			 ("run_id",ogr.OFTInteger)]
			
R_BUILDING_ABSPOS_DEF=[("km_name",ogr.OFTString),
				("scale",ogr.OFTReal),
				("dx",ogr.OFTReal),
				("dy",ogr.OFTReal),
				("n_points",ogr.OFTInteger),
				("run_id",ogr.OFTInteger)]
			
R_BUILDING_RELPOS_DEF=[("km_name",ogr.OFTString),
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
				("run_id",ogr.OFTInteger)]

B_AUTO_BUILDING_DEF=[("km_name",ogr.OFTString),
				 ("run_id",ogr.OFTInteger)]
				 
B_CLOUDS_DEF=[("km_name",ogr.OFTString),
				 ("run_id",ogr.OFTInteger)]

D_DELTA_ROADS_DEF=[("km_name",ogr.OFTString),
				("z_step_max",ogr.OFTReal),
				("z_step_min",ogr.OFTReal),
				("run_id",ogr.OFTInteger)]
				 
#The layers to create...			 
LAYERS={Z_CHECK_ROAD_TABLE:[ogr.wkbLineString25D,Z_CHECK_ROAD_DEF],
	Z_CHECK_BUILD_TABLE:[ogr.wkbPolygon25D,Z_CHECK_BUILD_DEF],
	Z_CHECK_ABS_TABLE:[ogr.wkbPoint25D,Z_CHECK_ABS_DEF],
	C_CHECK_TABLE:[ogr.wkbPolygon,C_CHECK_DEF],
	C_COUNT_TABLE:[ogr.wkbPolygon,C_COUNT_DEF],
	R_ROOFRIDGE_TABLE:[ogr.wkbLineString25D,R_ROOFRIDGE_DEF],
	R_ROOFRIDGE_STRIPS_TABLE:[ogr.wkbLineString25D,R_ROOFRIDGE_STRIPS_DEF],
	R_BUILDING_ABSPOS_TABLE:[ogr.wkbPolygon25D,R_BUILDING_ABSPOS_DEF],
	R_BUILDING_RELPOS_TABLE:[ogr.wkbPoint,R_BUILDING_RELPOS_DEF],
	D_DENSITY_TABLE:[ogr.wkbPolygon,D_DENSITY_DEF],
	B_AUTO_BUILDING_TABLE:[ogr.wkbPolygon,B_AUTO_BUILDING_DEF],
	B_CLOUDS_TABLE:[ogr.wkbPolygon,B_CLOUDS_DEF],
	D_DELTA_ROADS_TABLE:[ogr.wkbMultiPoint,D_DELTA_ROADS_DEF]
	}


RUN_ID=None   # A global id, which can be set from a wrapper script pr. process
SCHEMA_NAME="dhmqc"

def set_run_id(id):
	global RUN_ID
	RUN_ID=int(id)

def set_schema(name):
	global SCHEMA_NAME
	SCHEMA_NAME=name
	#Her gaar der lidt ged i det og bliver uskoent - Simon skal vist se lidt paa arkitekturen i det her	
	
	
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


#Base reporting class	
class ReportBase(object):
	LAYERNAME=None
	FIELD_DEFN=None #ordering of fields and type - might not necessarily reflect the ordering in the actual datasource - should reflect the order the arguments are reported in.
	def __init__(self,use_local,run_id=None):
		if use_local:
			print("Using local data source for reporting.")
		else:
			print("Using global data source for reporting.")
		#NOT VERY PRETTY!!! Simon vil du ikke lige give dette en overvejelse?? /Thor
		self.LAYERNAME = self.LAYERNAME.replace("dhmqc", SCHEMA_NAME)
		self.ds=get_output_datasource(use_local)
		if self.ds is not None:
			self.layer=self.ds.GetLayerByName(self.LAYERNAME)
			self.layerdefn=self.layer.GetLayerDefn()
		else:
			raise Warning("Failed to open data source- you might need to CREATE one...")
			self.layer=None
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
				defn=self.FIELD_DEFN[i]
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
	LAYERNAME=C_CHECK_TABLE
	FIELD_DEFN=C_CHECK_DEF

class ReportClassCount(ReportBase):
	LAYERNAME=C_COUNT_TABLE
	FIELD_DEFN=C_COUNT_DEF

class ReportZcheckAbs(ReportBase):
	LAYERNAME=Z_CHECK_ABS_TABLE
	FIELD_DEFN=Z_CHECK_ABS_DEF

class ReportRoofridgeCheck(ReportBase):
	LAYERNAME=R_ROOFRIDGE_TABLE
	FIELD_DEFN=R_ROOFRIDGE_DEF

class ReportRoofridgeStripCheck(ReportBase):
	LAYERNAME=R_ROOFRIDGE_STRIPS_TABLE
	FIELD_DEFN=R_ROOFRIDGE_STRIPS_DEF

class ReportBuildingAbsposCheck(ReportBase):
	LAYERNAME=R_BUILDING_ABSPOS_TABLE
	FIELD_DEFN=R_BUILDING_ABSPOS_DEF
	
class ReportBuildingRelposCheck(ReportBase):
	LAYERNAME=R_BUILDING_RELPOS_TABLE
	FIELD_DEFN=R_BUILDING_RELPOS_DEF

class ReportDensity(ReportBase):
	LAYERNAME=D_DENSITY_TABLE
	FIELD_DEFN=D_DENSITY_DEF

class ReportZcheckRoad(ReportBase):
	LAYERNAME=Z_CHECK_ROAD_TABLE
	FIELD_DEFN=Z_CHECK_ROAD_DEF

class ReportZcheckBuilding(ReportBase):
	LAYERNAME=Z_CHECK_BUILD_TABLE
	FIELD_DEFN=Z_CHECK_BUILD_DEF

class ReportAutoBuilding(ReportBase):
	LAYERNAME=B_AUTO_BUILDING_TABLE
	FIELD_DEFN=B_AUTO_BUILDING_DEF
	
class ReportClouds(ReportBase):
	LAYERNAME=B_CLOUDS_TABLE
	FIELD_DEFN=B_CLOUDS_DEF

class ReportDeltaRoads(ReportBase):
	LAYERNAME=D_DELTA_ROADS_TABLE
	FIELD_DEFN=D_DELTA_ROADS_DEF
	










	

	
	