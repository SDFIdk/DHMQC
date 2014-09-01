import sys,os,time
import numpy as np
from thatsDEM import pointcloud,vector_io,array_geometry,report

from thatsDEM.dhmqc_constants import *

def main(args):
	lasname=args[1]
	
	pc=pointcloud.fromLAS(lasname)
	n_points_total=pc.get_size()
	
	if n_points_total==0:
		print("Something is terribly terribly wrong here! Simon - vi skal melde en fjel")
	
	pc_temp=pc.cut_to_class(created_unused)
	n_created_unused=pc_temp.get_size()
	
	pc_temp=pc.cut_to_class(surface)
	n_surface=pc_temp.get_size()
	
	pc_temp=pc.cut_to_class(terrain)
	n_terrain=pc_temp.get_size()

	pc_temp=pc.cut_to_class(low_veg)
	n_low_veg=pc_temp.get_size()	

	pc_temp=pc.cut_to_class(high_veg)
	n_high_veg=pc_temp.get_size()	

	pc_temp=pc.cut_to_class(med_veg)
	n_med_veg=pc_temp.get_size()	

	pc_temp=pc.cut_to_class(building)
	n_building=pc_temp.get_size()

	pc_temp=pc.cut_to_class(outliers)
	n_outliers=pc_temp.get_size()

	pc_temp=pc.cut_to_class(mod_key)
	n_mod_key=pc_temp.get_size()

	pc_temp=pc.cut_to_class(water)
	n_water=pc_temp.get_size()
	
	pc_temp=pc.cut_to_class(ignored)
	n_ignored=pc_temp.get_size()

	pc_temp=pc.cut_to_class(bridge)
	n_bridge=pc_temp.get_size()

	pc_temp=pc.cut_to_class(man_excl)
	n_man_excl=pc_temp.get_size()
	
	kmname=get_tilename(lasname)
	polywkt=tilename_to_extent(kmname,return_wkt=True)
	print(polywkt)
	use_local="-use_local" in args
	reporter=report.ReportClassCount(use_local)
	reporter.report(kmname,n_created_unused,n_surface,n_terrain,n_low_veg,n_med_veg,n_high_veg,n_building,n_outliers,n_mod_key,n_water,n_ignored,n_bridge,n_man_excl,n_points_total,wkt_geom=polywkt)

if __name__=="__main__":
	main(sys.argv)