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
import sys,os,time,importlib
import traceback
import multiprocessing 
from qc.thatsDEM import report,array_geometry, vector_io
from qc.thatsDEM import dhmqc_constants as constants
from qc.utils import osutils  
from osgeo import ogr
import qc
import glob
import sqlite3
import argparse 


LOGDIR=os.path.join(os.path.dirname(__file__),"logs")


#argument handling
parser=argparse.ArgumentParser(description="Wrapper rutine for qc modules. Will use a sqlite database to manage multi-processing.")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("param_file",help="Input python parameter file.",nargs="?")
group.add_argument("-testhelp",help="Just print help for selected test.")
parser.add_argument("-runid",type=int,help="Specify runid for reporting. Will override a definition in paramater file.")


STATUS_PROCESSING=1
STATUS_OK=2
STATUS_ERROR=3

#SQL to create a local sqlite db - should be readable by ogr...
CREATE_DB="CREATE TABLE __tablename__ (id INTEGER PRIMARY KEY, wkt_geometry TEXT, tile_name TEXT, las_path TEXT, ref_path TEXT, prc_id INTEGER, exe_start TEXT, exe_end TEXT, status INTEGER, rcode INTEGER, msg TEXT)"



def usage(short=False):
	parser.print_help()
	if not short:
		print("+"*80)
		show_tests()
	sys.exit(1)


def show_tests():
	print("Currently valid tests:")
	for t in qc.tests:
		print("               "+t)




def run_check(p_number,testname,db_name,add_args,runid,use_local,schema,use_ref_data,lock):
	logger = multiprocessing.log_to_stderr()
	test_func=qc.get_test(testname)
	#Set up some globals in various modules... per process.
	if runid is not None:
		report.set_run_id(runid)
	if use_local:  #rather than sending args to scripts, which might not have implemented handling that particular argument, set a global attr in report.
		report.set_use_local(True)
	elif schema is not None:
		report.set_schema(schema)
	#LOAD THE DATABASE
	con=sqlite3.connect(db_name)
	if con is None:
		logger.error("[qc_wrap]: Process: {0:d}, unable to fetch process db".format(p_number))
		return
	
	cur=con.cursor()
	logname=testname+"_"+(time.asctime().split()[-2]).replace(":","_")+"_"+str(p_number)+".log"
	logname=os.path.join(LOGDIR,logname)
	logfile=open(logname,"w")
	stdout=osutils.redirect_stdout(logfile)
	stderr=osutils.redirect_stderr(logfile)
	sl="*-*"*23
	print(sl)
	print("[qc_wrap]: Running %s rutine at %s, process: %d, run id: %s" %(testname,time.asctime(),p_number,runid))
	print(sl)
	done=0
	cur.execute("select count() from "+testname+" where status=0")
	n_left=cur.fetchone()[0]
	while n_left>0:
		print(sl)
		print("[qc_wrap]: Number of tiles left: {0:d}".format(n_left))
		print(sl)
		#Critical section#
		lock.acquire()
		cur.execute("select id,las_path,ref_path from "+testname+" where status=0")
		data=cur.fetchone()
		if data is None:
			print("[qc_wrap]: odd - seems to be no more tiles left...")
			lock.release()
			break
		id,lasname,vname=data
		cur.execute("update "+testname+" set status=?,prc_id=?,exe_start=? where id=?",(STATUS_PROCESSING,p_number,time.asctime(),id))
		try:
			con.commit()
		except Exception,e:
			stderr.write("[qc_wrap]: Unable to update tile to finish status...\n"+str(e)+"\n")
			lock.release()
			break
		lock.release()
		#end critical section#
		print("[qc_wrap]: Doing lasfile {0:s}...".format(lasname))
		send_args=[testname,lasname]
		if use_ref_data:
			send_args.append(vname)
		send_args+=add_args
		try:
			rc=test_func(send_args)
		except Exception,e:
			rc=-1
			msg=str(e)
			status=STATUS_ERROR
			stderr.write("[qc_wrap]: Exception caught:\n"+msg+"\n")
			stderr.write("[qc_wrap]: Traceback:\n"+traceback.format_exc()+"\n")
		else:
			#set new status 
			msg="ok"
			status=STATUS_OK
			try:
				rc=int(rc)
			except:
				rc=0
		cur.execute("update "+testname+" set status=?,exe_end=?,rcode=?,msg=? where id=?",(status,time.asctime(),rc,msg,id))
		done+=1
		try:
			con.commit()
		except Exception,e:
			stderr.write("[qc_wrap]: Unable to update tile to finish status...\n"+str(e)+"\n")
		#go on to next one...
		cur.execute("select count() from "+testname+" where status=0")
		n_left=cur.fetchone()[0]
		
	print("[qc_wrap]: Checked %d tiles, finished at %s" %(done,time.asctime()))
	cur.close()
	con.close()
	#avoid writing to a closed fp...
	stdout.close()
	stderr.close()
	logfile.close()
	


def create_process_db(testname,matched_files):
	db_name=testname+"_{0:d}".format(int(time.time()))+".sqlite"
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
			
#names that must be defined in parameter file
NAMES=["TESTNAME","INPUT_TILE_CONNECTION"]
		
def main(args):
	pargs=parser.parse_args(args[1:])
	if pargs.testhelp is not None:
		if not pargs.testhelp in qc.tests:
			print(pargs.testhelp+" not mapped to any test.")
			show_tests()
		else:
			test_usage=qc.usage(pargs.testhelp)
			if test_usage is not None:
				test_usage()
			else:
				print("No usage defined in "+pargs.testhelp)
		return
	fargs=dict()
	try:
		execfile(pargs.param_file,fargs)
	except Exception,e:
		print("Failed to parse parameterfile:\n"+str(e))
		usage(short=True)
	for key in NAMES:
		if not key in fargs:
			print("The name "+key+" must be defined in parameter file")
			usage(short=True)
	
	testname=os.path.basename(fargs["TESTNAME"].replace(".py",""))
	if not testname in qc.tests:
		print("%s,defined in parameter file, not matched to any test (yet....)" %testname)
		show_tests()
		return
	#see if test uses ref-data and reference data is defined..
	use_ref_data=qc.tests[testname]
	ref_data_defined=False
	for key in ["REF_DATA_CONNECTION","REF_TILE_DB"]:
		ref_data_defined|=(key in fargs and fargs[key] is not None)
	if use_ref_data:
		if not ref_data_defined:
			print("Sorry, "+testname+" uses reference data.\nMust be defined in parameter file in either REF_DATA_CONNECTION or REF_TILE_DB!")
			usage(short=True)
	#import valid arguments from test
	test_parser=qc.get_argument_parser(testname)
	targs=fargs["TARGS"]
	if len(targs)>0: #validate targs
		print("Validating arguments for "+testname+"\n")
		if test_parser is not None:
			_targs=["dummy"]
			if use_ref_data:
				_targs.append("dummy")
			_targs.extend(targs)
			try:
				test_parser.parse_args(_targs)
			except Exception,e:
				print("Error parsing arguments for test script "+testname+":")
				print(str(e))
				return 1
		else:
			print("No argument parser in "+testname+" - unable to check arguments to test.")
		
	#test arguments for test script
	use_local=False
	if "USE_LOCAL" in fargs and (fargs["USE_LOCAL"] is not None):
		#will do nothing if it already exists
		#should be done 'process safe' so that its available for writing for the child processes...
		use_local=True
		report.create_local_datasource()
	#check the schema arg
	schema=None #use default schema
	if "SCHEMA" in fargs and fargs["SCHEMA"] is not None:
		if use_local: #mutually exclusive - actually checked by parser...
			print("Error: USE_LOCAL is True, local reporting database does not support schema names.")
			print("Will ignore SCHEMA")
		else:
			schema=fargs["SCHEMA"]
			#Test if we can open the global datasource with given schema
			ds=report.get_output_datasource()
			if ds is None:
				print("Unable to open global datasource...")
				return 1
			layers=report.LAYERS.keys()
			#only test if we can open one of the layers...
			layer_name=layers[0].replace(report.DEFAULT_SCHEMA_NAME,schema)
			layer=ds.GetLayerByName(layer_name)
			if layer is None:
				print("Unable to fetch layer "+layer_name+"\nSchema "+schema+" probably not created!")
				return 1
			layer=None
			ds=None
	
		
	#############
	## Get input tiles#
	#############
	print("Getting tiles from ogr datasource: "+fargs["INPUT_TILE_CONNECTION"])
	input_files=[]
	#improve by adding a layername
	ds=ogr.Open(fargs["INPUT_TILE_CONNECTION"])
	if ds is None:
		print("Failed to open input tile layer!")
		return 1
	if "INPUT_LAYER_SQL" in fargs and fargs["INPUT_LAYER_SQL"] is not None:
		print("Exceuting SQL to get input paths: "+fargs["INPUT_LAYER_SQL"])
		layer=ds.ExecuteSQL(fargs["INPUT_LAYER_SQL"])
		field_req=0
	else:
		print("No SQL defined. Assuming we want the first layer and attribute is called 'path'")
		field_req="path"
		layer=ds.GetLayer(0)
	assert(layer is not None)
	nf=layer.GetFeatureCount()
	for i in range(nf):
		feat=layer.GetNextFeature()
		#improve by adding path attr as arg
		path=feat.GetFieldAsString(field_req)
		if not os.path.exists(path):
			print("%s does not exist!" %path)
		else:
			input_files.append(path)
	#TODO: is it really necessary to call ds.ReleaseResultSet(layer)?? Or will the destructor do that?
	layer=None
	ds=None
	##############
	## End get input   #
	##############
	print("Found %d existing tiles." %len(input_files))
	if len(input_files)==0:
		print("Sorry, no input file(s) found.")
		usage()
	print("Running qc_wrap at %s" %(time.asctime()))
	if not os.path.exists(LOGDIR):
		print("Creating "+LOGDIR)
		os.mkdir(LOGDIR)
	##########################
	## Setup reference data if needed   #
	##########################
	ref_data_connection=None
	if use_ref_data:
		#test wheter we want tiled reference data...
		if "REF_DATA_CONNECTION" in fargs and fargs["REF_DATA_CONNECTION"] is not None:
			tiled_ref_data=False
			ref_data_connection=fargs["REF_DATA_CONNECTION"]
			print("A non-tiled reference datasource is specified.")
			print("Testing reference data connection....")
			ds=ogr.Open(ref_data_connection)
			if ds is None:
				print("Failed to open reference datasource.")
				return 1
			ds=None
			print("ok...")
			matched_files=[(name,ref_data_connection) for name in input_files] 
		else:
			tiled_ref_data=True
			print("Tiled reference data specified... getting corresponding tiles.")
			print("Assuming that "+ fargs["REF_TILE_DB"]+ " is created with the tile_coverage.py script (table name: coverage, tile_name and path attrs).")
			con=sqlite3.connect(fargs["REF_TILE_DB"])
			cur=con.cursor()
			matched_files=[]
			n_not_existing=0
			for name in input_files:
				tile_name=constants.get_tilename(name)
				cur.execute("select path from coverage where tile_name=?",(tile_name,))
				data=cur.fetchone()
				if data is None:
					print("Reference tile corresponding to "+name+" not found in db.")
					n_not_existing+=1
					continue
				ref_tile=data[0]
				if not os.path.exists(ref_tile):
					print("Reference tile "+ref_tile+" does not exist in the file system!")
					n_not_existing+=1
					continue
				matched_files.append((name,ref_tile))
			print("%d input tiles matched with reference tiles." %len(matched_files))
			print("%d non existing reference tiles." %(n_not_existing))
	else:  #else just append an empty string to the las_name...
		matched_files=[(name,"") for name in input_files] 
	####################
	## end setup reference data#
	####################
	
	###################
	## Start processing loop   #
	###################
	if len(matched_files)>0:
		#Create db for process control...
		lock=multiprocessing.Lock()
		db_name=create_process_db(testname,matched_files)
		if db_name is None:
			print("Something wrong - process control db not created.")
			return 1
		if "MP" in fargs and fargs["MP"]>0:
			mp=fargs["MP"]
		else:
			mp=multiprocessing.cpu_count()
		n_tasks=min(mp,len(matched_files))
		print("Starting %d process(es)." %n_tasks)
		if pargs.runid is not None:
			runid=pargs.runid
		elif "RUN_ID" in fargs and fargs["RUN_ID"] is not None:
			runid=int(fargs["RUN_ID"])
		else:
			runid=None
		if runid is not None:
			print("Run-id is set to: %d" %runid)
		print("Using process db: "+db_name)
		tasks=[]
		for i in range(n_tasks):
			p = multiprocessing.Process(target=run_check, args=(i,testname,db_name,targs,runid,use_local,schema,use_ref_data,lock))
			tasks.append(p)
			p.start()
		#Now watch the processing#
		con=sqlite3.connect(db_name)
		cur=con.cursor()
		n_todo=len(matched_files)
		n_crashes=0
		n_left=n_todo
		n_alive=n_tasks
		#start clock#
		t1=time.clock()
		t_last_report=0
		while n_alive>0 and n_left>0:
			time.sleep(5)
			cur.execute("select count() from "+testname+" where status>?",(STATUS_PROCESSING,))
			n_done=cur.fetchone()[0]
			n_alive=0
			for p in tasks:
				n_alive+=p.is_alive()
			#n_left: those tiles which have status 0 or STATUS_PROCESSING
			n_left=n_todo-n_done
			f_done=(float(n_done)/n_todo)*100
			now=time.clock()
			dt=now-t1
			dt_last_report=now-t_last_report
			if dt_last_report>15:
				cur.execute("select count() from "+testname+" where status=?",(STATUS_PROCESSING,))
				n_proc=cur.fetchone()[0]
				if n_done>0:
					t_left="{0:.2f} s".format(n_left*(dt/n_done))
				else:
					t_left="unknown"
				print("[qc_wrap - "+testname+"]: Done: {0:.1f} pct, tiles left: {1:d}, estimated time left: {2:s}, active: {3:d}".format(f_done,n_left,t_left,n_alive))
				cur.execute("select count() from "+testname+" where status=?",(STATUS_ERROR,))
				n_err=cur.fetchone()[0]
				if n_err>0:
					print("[qc_wrap]: {0:d} exceptions caught. Check sqlite-db.".format(n_err))
				t_last_report=now
			#Try to keep n_tasks alive... If n_left>n_alive, which means that there could be some with status 0 still left...
			if n_alive<n_tasks and n_left>n_alive:
				print("[qc_wrap]: A process seems to have stopped...")
				n_crashes+=1
		t2=time.clock()
		print("Running time %.2f s" %(t2-t1))
		cur.execute("select count() from "+testname+" where status>?",(STATUS_PROCESSING,))
		n_done=cur.fetchone()[0]
		cur.execute("select count() from "+testname+" where status=?",(STATUS_ERROR,))
		n_err=cur.fetchone()[0]
		print("[qc_wrap]: Did {0:d} tile(s).".format(n_done))
		if n_err>0:
			print("[qc_wrap]: {0:d} exceptions caught - check logfile(s)!".format(n_err))
		cur.close()
		con.close()
		
		
		
	
	print("qc_wrap finished at %s" %(time.asctime()))
	

if __name__=="__main__":
	main(sys.argv)