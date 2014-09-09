import sys,os,time,importlib
from multiprocessing import Process, Queue
from qc.thatsDEM import report,array_geometry
from qc.thatsDEM import dhmqc_constants as constants
from qc.utils import osutils  
import qc
import glob
import sqlite3
import argparse, shlex

LOGDIR=os.path.join(os.path.dirname(__file__),"logs")
MAX_PROCESSES=4

#argument handling
parser=argparse.ArgumentParser(description="Wrapper rutine for qc modules. Will use a sqlite database to manage multi-processing.",conflict_handler="resolve")
group = parser.add_mutually_exclusive_group()
group.add_argument("-schema",help="Set database schema. Only for global database.")
group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting. Should not be used with the -schema arg.")
parser.add_argument("-mp",help="Control the maximal number of processes to spawn. Defaults to 4.", default=MAX_PROCESSES)
parser.add_argument("-ext",help= "Specify extension of ref-data",default=".shp")
parser.add_argument("-single_dir",action="store_true",help= "Override the default layout for reference tiles. Specifies that reference tiles are located in a single dir!")
parser.add_argument("-runid", dest="runid",help="Specify id for this run. Will otherwise be NULL.",type=int)
parser.add_argument("-targs",help='Optional command line arguments to wrapped test. Quote the args, e.g. -targs "-zlim 0.2 -lines"')
#positional args
parser.add_argument("test",help="Specify which test to run.")
parser.add_argument("las_files",nargs="?",              #only optional if -usage is given. This way seems easiest...
help="""glob pattern of las files to run, e.g. c:\\test\\*.las or a list file containing paths to las files, one per line. 
If the pattern only matches one file, which does not end with 'las' a list file is assumed.""")
parser.add_argument("ref_tile_root",nargs="?", 
help="""
ONLY relevant for those checks which use vector data reference input. Root of a 'standard' directory of reference tiles clipped into 1km blocks and grouped in 10 km subdirs (layout defined in dhmqc_constants script). 
This directory must contain reference tiles of the appropriate geometry type for the chosen check.
""")


#SQL to create a local sqlite db - should be readable by ogr...
CREATE_DB="CREATE TABLE __tablename__ (id INTEGER PRIMARY KEY, wkt_geometry TEXT, tile_name TEXT, las_path TEXT, ref_path TEXT, prc_id INTEGER, exe_start TEXT, exe_end TEXT, status INTEGER)"



def usage(short=False):
	parser.print_help()
	print("Additional arguments will be passed on to the selected test script...")
	if not short:
		print("+"*80)
		print("Currently valid tests:")
		for t in qc.tests:
			print("               "+t)
	sys.exit(1)






def run_check(p_number,testname,db_name,add_args,runid,schema,use_ref_data):
	test_func=qc.get_test(testname)
	if runid is not None:
		report.set_run_id(runid)
	if schema is not None:
		report.set_schema(schema)
	#LOAD THE DATABASE
	con=sqlite3.connect(db_name)
	if con is None:
		print("Process: {0:d}, unable to fetch process db".format(p_number))
		return
	cur=con.cursor()
	logname=testname+"_"+(time.asctime().split()[-2]).replace(":","_")+"_"+str(p_number)+".log"
	logname=os.path.join(LOGDIR,logname)
	logfile=open(logname,"w")
	stdout=osutils.redirect_stdout(logfile)
	stderr=osutils.redirect_stderr(logfile)
	sl="*-*"*23
	print(sl)
	print("Running %s rutine at %s, process: %d, run id: %s" %(testname,time.asctime(),p_number,runid))
	print(sl)
	done=0
	cur.execute("select count() from '{0:s}' where status=0".format(testname))
	n_left=cur.fetchone()[0]
	while n_left>0:
		print(sl)
		print("Number of tiles left: {0:d}".format(n_left))
		print(sl)
		cur.execute("select id,las_path,ref_path from '{0:s}' where status=0".format(testname))
		data=cur.fetchone()
		if data is None:
			print("odd - seems to be no more tiles left...")
			break
		id,lasname,vname=data
		cur.execute("update '{0:s}' set status=1,prc_id={1:d},exe_start='{2:s}' where id='{3:d}'".format(testname,p_number,time.asctime(),id))
		try:
			con.commit()
		except Exception,e:
			print("Unable to update table:\n"+str(e))
			break
		print("Doing lasfile %s..." %lasname)
		send_args=[testname,lasname]
		if use_ref_data:
			send_args.append(vname)
		send_args+=add_args
		test_func(send_args)
		done+=1
		#set new status - TODO: set return code here also!!!
		cur.execute("update '{0:s}' set status=2,exe_end='{1:s}' where id='{2:d}'".format(testname,time.asctime(),id))
		try:
			con.commit()
		except Exception,e:
			print("Unable to update tile to finish status...\n"+str(e))
		#go on to next one...
		cur.execute("select count() from '{0:s}' where status=0".format(testname))
		n_left=cur.fetchone()[0]
		
	print("Checked %d tiles, finished at %s" %(done,time.asctime()))
	cur.close()
	con.close()
	#avoid writing to a closed fp...
	stdout.close()
	stderr.close()
	logfile.close()


def create_process_db(testname,matched_files):
	db_name=testname+"_"+"_".join(time.asctime().split()).replace(":","_")+".sqlite"
	con=sqlite3.connect(db_name)
	cur=con.cursor()
	cur.execute(CREATE_DB.replace("__tablename__",testname))
	id=0
	for lasname,vname in matched_files:
		tile=constants.get_tilename(lasname)
		wkt=constants.tilename_to_extent(tile,return_wkt=True)
		cur.execute("insert into "+testname+" (id,wkt_geometry,tile_name,las_path,ref_path,status) values (?,?,?,?,?,?)",(id,wkt,tile,lasname,vname,0)) 
		id+=1
	con.commit()
	cur.close()
	con.close()
	return db_name
			


		
def main(args):
	#We're in a dilemma here - need to parse the args before we can parse the args! At least we need to know which test to import before we can determine what the valid args are...
	#So make it simple and point out explicitely what the args to the test are...
	if len(args)<2:
		usage()
	pargs=parser.parse_args(args[1:])
	testname=os.path.basename(pargs.test.replace(".py",""))
	if not testname in qc.tests:
		print("%s not matched to any test (yet....)" %testname)
		usage()
	if pargs.las_files is None:
		#in this case just print the usage for test and exit...
		sys.argv[0]=testname
		test_usage=qc.usage(testname)
		if test_usage is not None:
			print("Usage for "+testname)
			test_usage()
		else:
			print("No usage for "+testname)
		sys.exit()
	#see if test uses ref-data and they are given...
	use_ref_data=qc.tests[testname]
	if use_ref_data!=bool(pargs.ref_tile_root): #None->False
		if use_ref_data:
			print("Sorry, "+testname+" uses reference data.")
		else:
			print("Sorry, "+testname+" does not use reference data.")
		usage(short=True)
	#import valid arguments from test
	test_parser=qc.get_argument_parser(testname)
	#test arguments for test script
	if pargs.targs is not None:
		targs=shlex.split(pargs.targs)
		if test_parser is not None:
			#add positional args to targs for parsing by test script parse
			_targs=[pargs.las_files]
			if use_ref_data:
				_targs.append(pargs.ref_tile_root)
			_targs.extend(targs)
			try:
				test_parser.parse_args(_targs)
			except Exception,e:
				print("Error parsing arguments for test script "+testname+":")
				print(str(e))
				return 1
				
		else:
			print("No argument parser in "+testname+" - unable to check arguments to test.")
	else:
		targs=[]
	if pargs.use_local:
		#will do nothing if it already exists
		#should be done 'process safe' so that its available for writing for the child processes...
		if not "-use_local" in targs:
			targs.append("-use_local")
		report.create_local_datasource()
	#consume the args that we do not want to send along...
	ext=pargs.ext
	if not ext.startswith("."):
		ext="."+ext
	if pargs.single_dir:
		simple_layout=True
		print("Assuming layout in a single dir...")
	else:
		simple_layout=False
	if pargs.schema is not None:
		schema=pargs.schema
		if pargs.use_local: #mutually exclusive - actually checked by parser...
			print("Error: use_local does not support schema names.")
			return
		#Test if we can open the global datasource with given schema
		ds=report.get_output_datasource()
		if ds is None:
			print("Unable to open global datasource...")
			return 
		layers=report.LAYERS.keys()
		#only test if we can open one of the layers...
		layer_name=layers[0].replace(report.DEFAULT_SCHEMA_NAME,schema)
		layer=ds.GetLayerByName(layer_name)
		if layer is None:
			print("Unable to fetch layer "+layer_name+"\nSchema "+schema+" probably not created!")
			return
		layer=None
		ds=None
	else:
		schema=None #use default schema
	
	
	las_files=glob.glob(pargs.las_files)
	if len(las_files)==0:
		print("Sorry, no input (las or list) file(s) found.")
		usage()
	if len(las_files)==1 and (not las_files[0].endswith("las")):
		print("Getting las files from input list...")
		list_file=las_files[0]
		las_files=[]
		f=open(list_file)
		for line in f:
			sline=line.strip()
			if len(sline)>0 and sline[0]!="#":
				if not os.path.exists(sline):
					print("%s does not exist!" %sline)
				else:
					las_files.append(sline)
		print("Found %d existing las filenames." %len(las_files))
		f.close()
	print("Running qc_wrap at %s" %(time.asctime()))
	if not os.path.exists(LOGDIR):
		os.mkdir(LOGDIR)
	t1=time.clock()
	if use_ref_data:
		ref_root=pargs.ref_tile_root
		if ref_root is None:
			print("Sorry this test requires reference data...")
			usage(short=True)
		if not os.path.exists(ref_root):
			print("Sorry, %s does not exist" %vector_root)
			usage(short=True)
		matched_files=[]
		for fname in las_files:
			try:
				ref_tile=constants.get_vector_tile(ref_root,fname,ext,simple_layout)
			except ValueError,e:
				print(str(e))
				continue
			if ref_tile is None:
				print("Reference tile corresponding to %s does not exist!" %os.path.basename(fname))
				continue
			matched_files.append((fname,ref_tile))
		print("%d las files matched with reference tiles." %len(matched_files))
	else:  #else just append an empty string to the las_name...
		matched_files=[(name,"") for name in las_files] 
		print("Found %d las files." %len(matched_files))
	
	if len(matched_files)>0:
		#Create db for process control...
		db_name=create_process_db(testname,matched_files)
		if db_name is None:
			print("Something wrong - process control db not created.")
			return 1
		n_tasks=min(pargs.mp,len(matched_files))
		print("Starting %d process(es)." %n_tasks)
		runid=pargs.runid
		if runid:
			print("Run id is set to: %d" %runid)
		tasks=[]
		for i in range(n_tasks):
			p = Process(target=run_check, args=(i,testname,db_name,targs,runid,schema,use_ref_data))
			tasks.append(p)
			p.start()
		for p in tasks:
			print("Joining...")
			p.join()
	t2=time.clock()
	print("Finished at %s" %(time.asctime()))
	print("Running time %.2f s" %(t2-t1))

if __name__=="__main__":
	main(sys.argv)