###################################
## Beginnings of a test-suite for the dhmqc system
## simlk, aug. 2014
###################################
import sys,os,time,importlib
import qc
from qc.utils import redirect_output
from qc.thatsDEM import report
import glob
LIB_DIR=os.path.join(os.path.dirname(__file__),"qc","lib")
DEMO_FOLDER=os.path.join(os.path.dirname(__file__),"demo")
LAS_DEMO=os.path.join(DEMO_FOLDER,"1km_6164_452.las")
WATER_DEMO=os.path.join(DEMO_FOLDER,"water_1km_6164_452.shp")
ROAD_DEMO=os.path.join(DEMO_FOLDER,"road_1km_6164_452.shp")
BUILDING_DEMO=os.path.join(DEMO_FOLDER,"buidling_1km_6164_452.shp")
DEMO_FILES=[LAS_DEMO,WATER_DEMO,ROAD_DEMO,BUILDING_DEMO]
OUTDIR=os.path.join(os.path.dirname(__file__),"test_output")
#just some nice strings
sl="*-*"*23
pl="+"*(len(sl))

#a testname, necessary files and additional arguments
TESTS={
"density_check": {"files":(LAS_DEMO,WATER_DEMO),"args":None}
}

def run_test(test,fct,files,stdout,stderr,args=None):
	print("Trying out: "+test)
	for name in files:
		if not os.path.exists(name):
			print("Necessary file: "+name+" does not exist.")
			return 0
	stdout.set_be_quiet(True)
	stderr.set_be_quiet(True)
	sargs=[test]+list(files)
	if args is not None:
		sargs.extend(args)
	print sargs
	try:
		ok=fct(sargs)
	except Exception,e:
		print("An exception occured:\n"+str(e))
		success=False
	else:
		success=(ok==0 or ok is None)
	stdout.set_be_quiet(False)
	stderr.set_be_quiet(False)
	if success:
		print("Success...")
	else:
		print("Fail! Details in log-file...")
	if success:
		return 0
	return 1
	

def main(args):
	
	if not os.path.exists(OUTDIR):
		os.mkdir(OUTDIR)
	logname=os.path.join(OUTDIR,"autotest_"+"_".join(time.asctime().split()).replace(":","_")+".log")
	logfile=open(logname,"w")
	stdout=redirect_output.redirect_stdout(logfile,be_quiet=False)
	stderr=redirect_output.redirect_stderr(logfile,be_quiet=False)
	print("Running dhmqc test suite at "+time.asctime())
	n_minor=0
	n_serious=0
	loaded_tests={}
	if True:
		#TODO: add a test to check if we should rebuild binaries.... i.e. if there are source modifications since last build...
		#For now see if lib-dir exists an is not empty...
		print(sl)
		print("Checking if binaries seem to be built...")
		files=glob.glob(os.path.join(LIB_DIR,"*lib*"))
		if len(files)==0:
			print("No *lib* files found in "+LIB_DIR)
			n_serious+=1
	# Import test
	if True:
		n_fails=0
		print(sl)
		print("See if we can import all tests.")
		for test in qc.tests:
			print(pl)
			print("Loading: "+test) 
			try:
				loaded_tests[test]=qc.get_test(test,reload=True)
			except Exception,e:
				print("An exception occured:\n"+str(e))
				n_fails+=1
			
		if n_fails==0:
			print("All tests loaded!")
		else:
			print("{0:d} tests failed to load!".format(n_fails))
		n_serious+=n_fails
	if True:
		#TODO - run some unit tests here...
		pass
	
	#Run some tests on the demo data...
	print(sl)
	print("Running tests on demo data...")
	try:
		ds=report.create_local_datasource(os.path.join(OUTDIR,"test_suite.sqlite"))
	except Exception,e:
		print("Unable to create a test-suite datasource:\n"+str(e))
	else:
		report.set_datasource(ds)
		for test in TESTS:
			print(sl)
			if test in loaded_tests:
				test_data=TESTS[test]
				n_serious+=run_test(test,loaded_tests[test],test_data["files"], stdout, stderr, test_data["args"])
				
			else:
				print(test+" was not loaded...")
			
			
	print("\n"+sl+"\n")
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