import os,sys
import argparse
import subprocess
import sqlite3
import time

import reflayers as rl

start_time = time.time()


parser=argparse.ArgumentParser(description="Python wrapper wrapping all class checks and gridding ")
parser.add_argument("tile_index",help="Path to tile index file.")
parser.add_argument("schema",help="database schema to report to.")
parser.add_argument("outdir",help="where to store output grid files.")
parser.add_argument("index_2007",help="Path to index of 2007 las files.")
#parser.add_argument("-runid",default=1, type=int, help="Run id. (defaults to 1")
pargs=parser.parse_args()
pargs.tile_index=os.path.abspath(pargs.tile_index).replace("\\","/")



if not os.path.exists(pargs.tile_index):
    print("Tile index must exist!")
    sys.exit(1)
	
mconn =sqlite3.connect(pargs.tile_index)
mc=mconn.cursor()
mc.execute("""select count(*) from coverage""")
amount_of_files=mc.fetchone()[0]
mconn.close()	
	
exestrings=[]
exestrings.append("""python class_check.py %s %s """ %(pargs.tile_index, pargs.schema))
exestrings.append("""python class_check.py %s %s -index_2007 %s""" %(pargs.tile_index, pargs.outdir, pargs.index_2007))


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
print "Summary of combined class check and gridding: "
print "  Files processed:      %d"%(amount_of_files)
print "  Total execution time: %.1f min" %(total_time/60)
print "  Average:              %.1f files/min" %(amount_of_files/(total_time/60))
print "------------------------------------------"
print " "
