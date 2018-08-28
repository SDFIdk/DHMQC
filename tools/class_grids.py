import os
import sys
import argparse
import subprocess
import sqlite3
import time
import multiprocessing

start_time = time.time()

parser = argparse.ArgumentParser(description="Python wrapper for class grids")
parser.add_argument("tile_index", help="Path to tile index file.")
parser.add_argument("outdir", help="Output folder.")
parser.add_argument("-index_2007", help="Path to index of 2007 las files.", default=None)
parser.add_argument("-only_dems", action="store_true",help="Only do dems and hillshade.")
parser.add_argument('-mp', default=multiprocessing.cpu_count(), type=int, help='Specify maximal number of processes to spawn (defaults to number of kernels).')

pargs = parser.parse_args()

mp = min(pargs.mp, multiprocessing.cpu_count())

DEV_PATH = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
qc_wrap = os.path.join(DEV_PATH, "qc_wrap.py -mp %s" % mp)
tile_coverage = os.path.join(DEV_PATH, "tile_coverage.py")

pargs.tile_index = os.path.abspath(pargs.tile_index).replace("\\", "/")
if pargs.index_2007 is not None:
    pargs.index_2007 = os.path.abspath(pargs.index_2007).replace("\\", "/")
if not os.path.exists(pargs.tile_index):
    print("Tile index must exist!")
    sys.exit(1)

mconn = sqlite3.connect(pargs.tile_index)
mc = mconn.cursor()
mc.execute("""select count(*) from coverage""")
amount_of_files = mc.fetchone()[0]
mconn.close()


if not os.path.exists(pargs.outdir):
    os.makedirs(pargs.outdir)
os.chdir(pargs.outdir)
for folder in ["class_grids", "dems", "diff", "hillshade_dtm", "hillshade_dsm"]:
    if not os.path.exists(folder):
        os.mkdir(folder)

if not pargs.only_dems:
    call = 'python %s -testname class_grid -targs "class_grids -cs 1" -tiles %s' % (qc_wrap, pargs.tile_index)
    rc = subprocess.call(call, shell=True)
    print rc
    subprocess.call("gdalbuildvrt class_grid.vrt class_grids/*.tif", shell=True)
    subprocess.call("gdaladdo -ro --config COMPRESS_OVERVIEW LZW class_grid.vrt 2 4 8 16", shell=True)
    if pargs.index_2007 is not None and os.path.exists(pargs.index_2007):
        call = 'python %s -testname pointcloud_diff -targs "-cs 4.0 -class 5 -toE -outdir diff" -tiles %s -reftiles %s' % (qc_wrap, pargs.tile_index, pargs.index_2007)
        rc = subprocess.call(call, shell=True)
        subprocess.call("gdalbuildvrt diff.vrt diff/*.tif", shell=True)
        subprocess.call("gdaladdo -ro --config COMPRESS_OVERVIEW LZW diff.vrt  2 4 8 16", shell=True)

subprocess.call('python ' + qc_wrap +' -testname dem_gen_new -tiles ' + pargs.tile_index +' -targs "' + pargs.tile_index + ' dems -dtm -dsm -nowarp -overwrite"', shell=True)

if os.path.exists("dtm.sqlite"):
    os.remove("dtm.sqlite")
if os.path.exists("dsm.sqlite"):
    os.remove("dsm.sqlite")

subprocess.call('python ' + tile_coverage + ' create dems tif dtm.sqlite --fpat dtm', shell=True)
subprocess.call('python ' + tile_coverage + ' create dems tif dsm.sqlite --fpat dsm', shell=True)
call = 'python %s -testname hillshade -tiles dtm.sqlite -targs "hillshade_dtm -tiledb dtm.sqlite"' % qc_wrap
subprocess.call(call, shell=True)
call = 'python %s -testname hillshade -tiles dsm.sqlite -targs "hillshade_dsm -tiledb dsm.sqlite"' % qc_wrap
subprocess.call(call, shell=True)
subprocess.call("gdalbuildvrt dtm_shade.vrt hillshade_dtm/*.tif", shell=True)
subprocess.call("gdalbuildvrt dsm_shade.vrt  hillshade_dsm/*.tif", shell=True)
subprocess.call("gdaladdo -ro --config COMPRESS_OVERVIEW LZW -r gauss dtm_shade.vrt 4 8 16 32", shell=True)
subprocess.call("gdaladdo -ro --config COMPRESS_OVERVIEW LZW -r gauss dsm_shade.vrt 4 8 16 32", shell=True)

end_time = time.time()

total_time = end_time - start_time

print " "
print " "
print "------------------------------------------"
print "Summary: "
print "  Files processed:      %d" % (amount_of_files)
print "  Total execution time: %.1f min" % (total_time / 60)
print "  Average:              %.1f files/min" % (amount_of_files / (total_time / 60))
print "------------------------------------------"
print " "
