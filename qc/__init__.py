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
"z_accuracy_gcp": True,
"z_precision_buildings": True,
"z_precision_roads": True,
"las2polygons":False,
"road_delta_check":True,
"spike_check":False,
"steep_triangles":False,
"wobbly_water":False,
"dem_gen":False,
"class_grid":False,
"dem_gen_new":False}

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
	


		