#init file for qc module
#all tests to be wrapped defined below
#format: module_name, boolean which indicates whether or not reference data is used (vector, las, etc.)
import importlib
tests={
"classification_check": True,
"count_classes":False,
"density_check":True,
"pointcloud_diff": True,
"roof_ridge_alignment":True,
"roof_ridge_strip": True,
"xy_accuracy_buildings":True,
"xy_precision_buildings":True,
"z_accuracy": True,
"z_precision_buildings": True,
"z_precision_roads": True,
"las2polygons":False}

test_module=None

def get_test(name):
	global test_module
	if test_module is None:
		test_module=importlib.import_module("."+name,"qc")
	return test_module.main

def usage(name):
	global test_module
	if test_module is None:
		test_module=importlib.import_module("."+name,"qc")
	if hasattr(test_module,"usage"):
		return test_module.usage
	return None
	


		