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
import sys,os,time
import numpy as np
from thatsDEM import pointcloud
from db import report
from dhmqc_constants import *
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Count points per class in a tile",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
#add some arguments below
parser.add_argument("las_file",help="input las tile.")

def usage():
    parser.print_help()

def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception,e:
        print(str(e))
        return 1
    kmname=get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
    if pargs.schema is not None:
        report.set_schema(pargs.schema)
    reporter=report.ReportClassCount(pargs.use_local)
    pc=pointcloud.fromLAS(pargs.las_file)
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
    
    #new classes
    pc_temp=pc.cut_to_class(high_noise)
    n_high_noise=pc_temp.get_size()
    
    pc_temp=pc.cut_to_class(power_line)
    n_power_line=pc_temp.get_size()
    
    pc_temp=pc.cut_to_class(terrain_in_buildings)
    n_terrain_in_buildings=pc_temp.get_size()
    
    pc_temp=pc.cut_to_class(low_veg_in_buildings)
    n_low_veg_in_buildings=pc_temp.get_size()
    

    pc_temp=pc.cut_to_class(man_excl)
    n_man_excl=pc_temp.get_size()
    
    
    polywkt=tilename_to_extent(kmname,return_wkt=True)
    print(polywkt)
    
    reporter.report(kmname,n_created_unused,n_surface,n_terrain,n_low_veg,n_med_veg,
    n_high_veg,n_building,n_outliers,n_mod_key,n_water,n_ignored,n_power_line,n_bridge,n_high_noise,n_terrain_in_buildings,n_low_veg_in_buildings,
    n_man_excl,n_points_total,wkt_geom=polywkt)

if __name__=="__main__":
    main(sys.argv)