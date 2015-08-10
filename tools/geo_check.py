import os,sys
import argparse
import subprocess
import sqlite3
import time
import reflayers as rl

start_time = time.time()

DEV_PATH=os.path.realpath(os.path.join(os.path.dirname(__file__),".."))
qc_wrap=os.path.join(DEV_PATH,"qc_wrap.py")
tile_coverage=os.path.join(DEV_PATH,"tile_coverage.py")

parser=argparse.ArgumentParser(description="Python wrapper for geometric checks")
parser.add_argument("tile_index",help="Path to tile index file.")
parser.add_argument("schema",help="database schema to report to.")
parser.add_argument("outdir",help="where to put grid files")
parser.add_argument("-runid",default=1, type=int, help="Run id. (defaults to 1")
pargs=parser.parse_args()
pargs.tile_index=os.path.abspath(pargs.tile_index).replace("\\","/")

RUNID=str(pargs.runid)

if not os.path.exists(pargs.tile_index):
    print("Tile index must exist!")
    sys.exit(1)

	
mconn =sqlite3.connect(pargs.tile_index)
mc=mconn.cursor()
mc.execute("""select count(*) from coverage""")
amount_of_files=mc.fetchone()[0]
mconn.close()
	
density_dir=pargs.outdir+'/density_grid'
if not os.path.exists(density_dir):
	os.makedirs(density_dir)

exestrings=[]
exestrings.append("""python %s/qc_wrap.py %s/args/density_args.py -runid %s -refcon "%s" -schema %s -tiles %s -targs "-outdir %s" """ %(DEV_PATH, DEV_PATH, RUNID, rl.REFCON, pargs.schema, pargs.tile_index, density_dir)) 
exestrings.append("""gdalbuildvrt -a_srs epsg:25832 %s.vrt %s/*.asc""" %(density_dir, density_dir))
exestrings.append("""gdaladdo -ro --config COMPRESS_OVERVIEW LZW %s.vrt  2 4 8 16""" %(density_dir))
exestrings.append("""python %s/qc_wrap.py %s/args/mcCloud_args.py -runid %s -refcon "%s" -schema %s -tiles %s """ %(DEV_PATH, DEV_PATH, RUNID, rl.REFCON, pargs.schema, pargs.tile_index))
#exestrings.append("""python %s/qc_wrap.py %s/args/z_accuracy_args.py -runid %s -refcon "%s" -schema %s -tiles %s """ %(DEV_PATH, DEV_PATH, RUNID, rl.REFCON, pargs.schema, pargs.tile_index))
exestrings.append("""python %s/qc_wrap.py %s/args/Z_precision_roads_args.py -runid %s -refcon "%s" -schema %s -tiles %s """ %(DEV_PATH, DEV_PATH, RUNID, rl.REFCON, pargs.schema, pargs.tile_index))
exestrings.append("""python %s/qc_wrap.py %s/args/roof_ridge_strip_args.py -runid %s -refcon "%s" -schema %s -tiles %s """ %(DEV_PATH, DEV_PATH, RUNID, rl.REFCON, pargs.schema, pargs.tile_index))
exestrings.append("""python %s/qc_wrap.py %s/args/roof_ridge_align_args.py -runid %s -refcon "%s" -schema %s -tiles %s """ %(DEV_PATH, DEV_PATH, RUNID, rl.REFCON, pargs.schema, pargs.tile_index))
exestrings.append("""python %s/qc_wrap.py %s/args/gcp_args.py -runid %s -refcon "%s" -schema %s -tiles %s """ %(DEV_PATH, DEV_PATH, RUNID, rl.REFCON, pargs.schema, pargs.tile_index))

for exestring in exestrings:
	print "-------------------"
	print exestring
	print "-------------------"
	subprocess.call(exestring,shell=True)
	
end_time = time.time()

total_time=end_time-start_time

print " "
print " "
print "------------------------------------------"
print "Summary: "
print "  Files processed:      %d"%(amount_of_files)
print "  Total execution time: %.1f min" %(total_time/60)
print "  Average:              %.1f files/min" %(amount_of_files/(total_time/60))
print "------------------------------------------"
print " "
 

