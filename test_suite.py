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
###################################
## Beginnings of a test-suite for the dhmqc system
## simlk, aug. 2014
###################################
import sys,os,time,importlib
import qc
from qc.utils import osutils 
from qc.thatsDEM import pointcloud, slash, array_geometry, triangle
from qc.db import report
import glob
from argparse import ArgumentParser
import traceback

HERE=os.path.dirname(__file__)
C_SOURCE_FOLDER=os.path.join(HERE,"src")
LIB_DIR=os.path.join(HERE,"qc","lib")
DEMO_FOLDER=os.path.join(HERE,"demo")
LAS_DEMO=os.path.join(DEMO_FOLDER,"1km_6173_632.las")
WATER_DEMO=os.path.join(DEMO_FOLDER,"water_1km_6173_632.geojson")
ROAD_DEMO=os.path.join(DEMO_FOLDER,"roads_1km_6173_632.geojson")
BUILDING_DEMO=os.path.join(DEMO_FOLDER,"build_1km_6173_632.geojson")
DEMO_FILES=[LAS_DEMO,WATER_DEMO,ROAD_DEMO,BUILDING_DEMO]
OUTDIR=os.path.join(HERE,"test_output")
OUTPUT_DS=os.path.join(OUTDIR,"test_suite.sqlite")
#just some nice strings
sl="*-*"*23
pl="+"*(len(sl))
#hmm not pretty right now - will construct a sequence of args from files and args (can put everything in args if we dont need the os.path.exists...)...
UNIT_TESTS=[
("pointcloud",{"fct": pointcloud.unit_test,"files":[LAS_DEMO],"args":None}),
("array_geometry",{"fct":array_geometry.unit_test,"files":[],"args":None}),
("triangle",{"fct":triangle.unit_test,"files":[],"args":None}),
("slash",{"fct": slash.unit_test,"files":[LAS_DEMO],"args":None})
]
#a testname, necessary files and additional arguments
TESTS=[
("density_check", {"files":[LAS_DEMO,WATER_DEMO],"args":None}),
("z_precision_roads",{"files":[LAS_DEMO,ROAD_DEMO],"args":None}),
("z_precision_buildings",{"files":[LAS_DEMO,BUILDING_DEMO],"args":None}),
("roof_ridge_strip",{"files":[LAS_DEMO,BUILDING_DEMO],"args":["-search_factor","1.1","-use_all"]}),
("spike_check",{"files":[LAS_DEMO],"args":["-zlim","0.08","-slope","8"]}),
("z_accuracy",{"files":[LAS_DEMO,ROAD_DEMO],"args":["-lines","-toE"]}),
("classification_check",{"files":[LAS_DEMO,BUILDING_DEMO],"args":["-below_poly","-toE"]}),
("count_classes",{"files":[LAS_DEMO],"args":None}),
("las2polygons",{"files":[LAS_DEMO],"args":None}),
("las2polygons",{"files":[LAS_DEMO],"args":["-height","300"]}),
("road_delta_check",{"files":[LAS_DEMO,ROAD_DEMO],"args":["-zlim","0.1"]}),
("roof_ridge_alignment",{"files":[LAS_DEMO,BUILDING_DEMO],"args":["-use_all","-search_factor","1.1"]}),
("xy_accuracy_buildings",{"files":[LAS_DEMO,BUILDING_DEMO],"args":None}),
("xy_precision_buildings",{"files":[LAS_DEMO,BUILDING_DEMO],"args":None}),
("wobbly_water",{"files":[LAS_DEMO],"args":None}),
("dvr90_wrapper",{"files":[LAS_DEMO],"args":[OUTDIR]}),
("pc_repair_man",{"files":[LAS_DEMO],"args":[OUTDIR,"-doall","-olaz"]})
]

TEST_NAMES=[test[0] for test in TESTS]

progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Test suite for dhmqc",prog=progname)
#add some arguments below
parser.add_argument("--test",help="Only run this test - else run everything", choices=TEST_NAMES)


def run_test(test,fct,files,stdout,stderr,args=None, call_as_main=True):
	print("Trying out: "+test)
	for name in files:
		if not os.path.exists(name):
			print("Necessary file: "+name+" does not exist.")
			return 0
	stdout.set_be_quiet(True)
	if call_as_main:
		sargs=[test]
	else:
		sargs=[]
	sargs.extend(files)
	if args is not None:
		sargs.extend(args)
	t1=time.clock()
	try:
		if call_as_main:
			ok=fct(sargs)
		else:
			ok=fct(*sargs)
	except Exception,e:
		print("An exception occured:\n"+str(e))
		print(traceback.format_exc())
		success=False
	else:
		success=(ok==0 or ok is None)
	t2=time.clock()
	stdout.set_be_quiet(False)
	if success:
		print("Success... took: {0:.2f} s".format(t2-t1))
	else:
		print("Fail! Details in log-file...")
	if success:
		return 0
	return 1
	

def main(args):
	pargs=parser.parse_args(args[1:])
	if not os.path.exists(OUTDIR):
		os.mkdir(OUTDIR)
	logname=os.path.join(OUTDIR,"autotest_"+"_".join(time.asctime().split()).replace(":","_")+".log")
	logfile=open(logname,"w")
	stdout=osutils.redirect_stdout(logfile,be_quiet=False)
	stderr=osutils.redirect_stderr(logfile,be_quiet=False)
	print("Running dhmqc test suite at "+time.asctime())
	print("Details in logfile: "+logname)
	print("Output spatialite db in: "+OUTPUT_DS)
	n_minor=0
	n_serious=0
	loaded_tests={}
	if True:
		print(sl)
		print("Checking if binaries seem to be built...")
		files=glob.glob(os.path.join(LIB_DIR,"*.exe"))
		if len(files)==0:
			print("No *.exe files found in "+LIB_DIR)
			n_serious+=1
		else:
			lib_mod_time=0
			for name in files:
				lib_mod_time=max(lib_mod_time,os.path.getmtime(name))
			source_mod_time=0
			for root,dirs,files in os.walk(C_SOURCE_FOLDER):
				for name in files:
					if name.endswith(".h") or name.endswith(".c"):
						source_mod_time=max(source_mod_time,os.path.getmtime(os.path.join(root,name)))
						
			if source_mod_time>lib_mod_time:
				print("There seem to be source modifactions after last build.. Perhaps rebuild c-source?")
				n_minor+=1
			else:
				print("Seems to be ok")
			
						
			
	# Import test
	if True:
		n_fails=0
		print(sl)
		print("See if we can import all tests.")
		for test in qc.tests:
			print(pl)
			print("Loading: "+test)
			stdout.set_be_quiet(True)
			try:
				loaded_tests[test]=qc.get_test(test)
			except Exception,e:
				print("An exception occured:\n"+str(e))
				n_fails+=1
				success=False
			else:
				success=True
			stdout.set_be_quiet(False)
			if success:
				print("Success...")
			else:
				print("Failed - details in log file...")
			
		print(pl)	
		if n_fails==0:
			print("All tests loaded!")
		else:
			print("{0:d} tests failed to load!".format(n_fails))
		n_serious+=n_fails
	if True:
		print(sl)
		print("Running unit tests...")
		for test,test_data in UNIT_TESTS:
			print(pl)
			n_serious+=run_test(test,test_data["fct"],test_data["files"],stdout,stderr,test_data["args"],call_as_main=False)
	
	#Run some tests on the demo data...
	print(sl)
	print("Running tests on demo data...")
	try:
		ds=report.create_local_datasource(OUTPUT_DS)
	except Exception,e:
		print("Unable to create a test-suite datasource:\n"+str(e))
		n_serious+=1
	else:
		report.set_datasource(ds)
		report.set_run_id(int(time.time())) #a time stamp
		for test,test_data in TESTS:
			if pargs.test is None or pargs.test==test:
				print(sl)
				if test in loaded_tests:
					n_serious+=run_test(test,loaded_tests[test],test_data["files"], stdout, stderr, test_data["args"])
				else:
					print(test+" was not loaded...")
			
	print(sl+"\n")
	print("Minor errors  : {0:d}".format(n_minor))
	print("Serious errors: {0:d}".format(n_serious))
	if n_serious==0:
		print("Yipiieee!!")
	#avoid writing to a closed fp...
	stdout.close()
	stderr.close()
	logfile.close()
	return n_serious
	

if __name__=="__main__":
	sys.exit(main(sys.argv))
