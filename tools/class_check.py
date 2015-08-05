import os,sys
import argparse
import subprocess
import reflayers as rl
DEV_PATH=os.path.realpath(os.path.join(os.path.dirname(__file__),".."))
qc_wrap=os.path.join(DEV_PATH,"qc_wrap.py")
tile_coverage=os.path.join(DEV_PATH,"tile_coverage.py")

parser=argparse.ArgumentParser(description="Python wrapper for class checks")
parser.add_argument("tile_index",help="Path to tile index file.")
parser.add_argument("schema",help="database schema to report to.")
parser.add_argument("-runid",default=1, type=int, help="Run id. (defaults to 1")
pargs=parser.parse_args()
pargs.tile_index=os.path.abspath(pargs.tile_index).replace("\\","/")

RUNID=str(pargs.runid)


if not os.path.exists(pargs.tile_index):
    print("Tile index must exist!")
    sys.exit(1)

exestrings=[]
exestrings.append( """python %s/qc_wrap.py -testname spike_check -schema %s -targs "-zlim 0.25" -tiles %s -runid %s""" %(DEV_PATH, pargs.schema, pargs.tile_index, RUNID))
exestrings.append("""python %s/qc_wrap.py -testname count_classes -schema %s -tiles %s -runid %s""" %(DEV_PATH,pargs.schema, pargs.tile_index, RUNID))
exestrings.append("""python %s/qc_wrap.py -testname classification_check -schema %s -tiles %s -runid %s -refcon "%s" -targs "-type building -layersql '%s'"  """ %(DEV_PATH, pargs.schema, pargs.tile_index, RUNID, rl.REFCON, rl.HOUSES))
exestrings.append("""python %s/qc_wrap.py -testname classification_check -schema %s -tiles %s -runid %s -refcon "%s" -targs "-type lake -layersql '%s'"  """ %(DEV_PATH, pargs.schema, pargs.tile_index, RUNID, rl.REFCON, rl.LAKES))
exestrings.append("""python %s/qc_wrap.py -testname road_delta_check -schema %s -tiles %s -runid %s -refcon "%s" -targs "-layersql '%s' -zlim 0.5" """%(DEV_PATH, pargs.schema, pargs.tile_index, RUNID, rl.REFCON,rl.ROADS))
exestrings.append("""python %s/qc_wrap.py -testname classification_check -schema %s -tiles %s -runid %s -refcon "%s" -targs "-layersql '%s' -below_poly -toE" """%(DEV_PATH, pargs.schema, pargs.tile_index, RUNID, rl.REFCON,rl.HOUSES))
exestrings.append("""python %s/qc_wrap.py -testname las2polygons -schema %s -tiles %s -runid %s"""%(DEV_PATH, pargs.schema, pargs.tile_index, RUNID))
exestrings.append("""python %s/qc_wrap.py -testname wobbly_water -schema %s -tiles %s -runid %s"""%(DEV_PATH, pargs.schema, pargs.tile_index, RUNID))


for exestring in exestrings:
	print "-------------------"
	print exestring
	print "-------------------"
	subprocess.call(exestring,shell=True)
	

