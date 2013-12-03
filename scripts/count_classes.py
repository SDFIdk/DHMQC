import sys,os,time
import numpy as np
from thatsDEM import pointcloud,vector_io,array_geometry,report
from utils.names import get_1km_name
from utils.stats import get_dz_stats


created_unused=0
surface=1
terrain=2
low_veg=3
med_veg=4
high_veg=5
building=6
outliers=7
mod_key=8
water=9
ignored=10
bridge=17
man_excl=32

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
	
	strlist=os.path.basename(lasname).rsplit('.')
	strlist=strlist[0].rsplit('_')
	print(strlist[1])
	ly=int(strlist[1])*1000
	lx=int(strlist[2])*1000
	ux=lx+1000
	uy=ly+1000
	kmname='1km_'+strlist[1]+'_'+strlist[2]
	polywkt='POLYGON((%f %f,%f %f, %f %f, %f %f, %f %f))' %(lx,ly,lx,uy,ux,uy,ux,ly,lx,ly)
	print(polywkt)
	
	use_local="-use_local" in args
	ds_report=report.get_output_datasource(use_local)	
	if use_local:
		print("Using local data source for reporting.")
	else:
		print("Using global data source for reporting.")	
	
	
	report.report_class_count(ds_report,kmname,n_created_unused,n_surface,n_terrain,n_low_veg,n_med_veg,n_high_veg,n_building,n_outliers,n_mod_key,n_water,n_ignored,n_bridge,n_man_excl,n_points_total,wkt_geom=polywkt)
	
	

if __name__=="__main__":
	main(sys.argv)