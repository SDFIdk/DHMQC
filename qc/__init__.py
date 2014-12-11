#init file for qc module
#all tests to be wrapped defined below
#format: module_name, boolean which indicates whether or not reference data is used (vector, las, etc.)
import importlib
tests={
"classification_check": True,
"count_classes":False,
"density_check":True,
"point_distance":True,
"pointcloud_diff": True,
"roof_ridge_alignment":True,
"roof_ridge_strip": True,
"xy_accuracy_buildings":True,
"xy_precision_buildings":True,
"z_accuracy": True,
"z_precision_buildings": True,
"z_precision_roads": True,
"las2polygons":False,
"road_delta_check":True,
"spike_check":False,
"steep_triangles":False,
"wobbly_water":False,
"dem_gen":False,
"dtm_gen":False,
"dsm_gen":False,
"dem_gen2":False}

loaded_modules={}


def get_module(name):
	if not name in loaded_modules:
		loaded_modules[name]=importlib.import_module("."+name,"qc")
	return loaded_modules[name]
	

def get_test(name):
	m=get_module(name)
	return m.main

def usage(name):
	m=get_module(name)
	if hasattr(m,"usage"):
		return m.usage
	return None

#method to add valid arguments to an argument parser in e.g. a wrapper...
def get_argument_parser(name):
	m=get_module(name)
	if hasattr(m,"parser"):
		return m.parser
	return None
	


		