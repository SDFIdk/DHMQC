from __future__ import print_function
import os,sys
import argparse
import subprocess
import sqlite3
import time
import multiprocessing

import reflayers as rl

start_time = time.time()

parser=argparse.ArgumentParser(description="Python wrapper for class checks")
parser.add_argument("tile_index",help="Path to tile index file.")
parser.add_argument("schema",help="database schema to report to.")
parser.add_argument("-runid",default=1, type=int, help="Run id. (defaults to 1")
parser.add_argument("-mp", default=multiprocessing.cpu_count(), type=int, help='Specify maximal number of processes to spawn (defaults to number of kernels).')
pargs=parser.parse_args()
pargs.tile_index=os.path.abspath(pargs.tile_index).replace("\\","/")

mp = min(pargs.mp, multiprocessing.cpu_count())

DEV_PATH=os.path.realpath(os.path.join(os.path.dirname(__file__),".."))
qc_wrap=os.path.join(DEV_PATH,"qc_wrap.py -mp %s" % mp)
tile_coverage=os.path.join(DEV_PATH,"tile_coverage.py")

RUNID=str(pargs.runid)


if not os.path.exists(pargs.tile_index):
    print("Tile index must exist!")
    sys.exit(1)

mconn =sqlite3.connect(pargs.tile_index)
mc=mconn.cursor()
mc.execute("""select count(*) from coverage""")
amount_of_files=mc.fetchone()[0]
mconn.close()

exestrings=[]
exestrings.append("""python %s -testname spike_check -schema %s -targs "-zlim 0.25" -tiles %s -runid %s""" % (qc_wrap, pargs.schema, pargs.tile_index, RUNID))
exestrings.append("""python %s -testname count_classes -schema %s -tiles %s -runid %s""" % (qc_wrap,pargs.schema, pargs.tile_index, RUNID))
exestrings.append("""python %s -testname classification_check -schema %s -tiles %s -runid %s -refcon "%s" -targs "-type building -layersql '%s'"  """ % (qc_wrap, pargs.schema, pargs.tile_index, RUNID, rl.REFCON, rl.HOUSES))
exestrings.append("""python %s -testname classification_check -schema %s -tiles %s -runid %s -refcon "%s" -targs "-type lake -layersql '%s'"  """ % (qc_wrap, pargs.schema, pargs.tile_index, RUNID, rl.REFCON, rl.LAKES))
exestrings.append("""python %s -testname road_delta_check -schema %s -tiles %s -runid %s -refcon "%s" -targs "-layersql '%s' -zlim 0.5" """ % (qc_wrap, pargs.schema, pargs.tile_index, RUNID, rl.REFCON,rl.ROADS))
exestrings.append("""python %s -testname classification_check -schema %s -tiles %s -runid %s -refcon "%s" -targs "-layersql '%s' -below_poly -toE" """ % (qc_wrap, pargs.schema, pargs.tile_index, RUNID, rl.REFCON,rl.HOUSES))
exestrings.append("""python %s -testname las2polygons -schema %s -tiles %s -runid %s""" % (qc_wrap, pargs.schema, pargs.tile_index, RUNID))
exestrings.append("""python %s -testname wobbly_water -schema %s -tiles %s -runid %s""" % (qc_wrap, pargs.schema, pargs.tile_index, RUNID))


for exestring in exestrings:
	print("-------------------")
	print(exestring)
	print("-------------------")
	subprocess.call(exestring,shell=True)


end_time = time.time()

total_time=end_time-start_time

print(" ")
print(" ")
print("------------------------------------------")
print("Summary: ")
print("  Files processed:      %d"%(amount_of_files))
print("  Total execution time: %.1f min" %(total_time/60))
print("  Average:              %.1f files/min" %(amount_of_files/(total_time/60)))
print("------------------------------------------")
print(" ")
