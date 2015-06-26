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
import subprocess
from qc.thatsDEM import array_geometry, vector_io, remote_files
from qc.db import report
from qc import dhmqc_constants as constants
from qc.utils import osutils  
from osgeo import ogr
import qc
import glob
import sqlite3
import argparse 
import shlex


LOGDIR=os.path.join(os.path.dirname(__file__),"logs")





STATUS_PROCESSING=1
STATUS_OK=2
STATUS_ERROR=3

#SQL to create a local sqlite db - should be readable by ogr...
CREATE_DB="CREATE TABLE __tablename__ (id INTEGER PRIMARY KEY, wkt_geometry TEXT, tile_name TEXT, las_path TEXT, ref_path TEXT, prc_id INTEGER, exe_start TEXT, exe_end TEXT, status INTEGER, rcode INTEGER, msg TEXT)"

#NAMES WHICH CAN BE DEFINED IN PARAM-FILE:
#Use tile_coverage.py to set up input and reference tile_layers 
#TESTNAME="some_test"
#INPUT_TILE_CONNECTION="some ogr-readable layer containing tilenames"
#INPUT_LAYER_SQL="OGR - sql to select path attributte of tiles" #e.g. select path from coverage, or select some_field as path from some_layer where some_attr=some_value
#DB-setup for reporting of test results
#USE_LOCAL=True  #Use local db for reporting (instead of PostGIS-layer) 
#SCHEMA=None #"Some Postgres schema e.g. blockxx_2015" only relevant if USE_LOCAL is False
#if test is using reference data - one of these names must be defined, listed in order of precedence
#REF_DATA_CONNECTION="a db connection or path to a seamless vector datasource - for vector data which is not tiled"
#REF_TILE_DB="path to an ogr readable tile layer" #if REF_DATA_CONNECTION is not defined, this must point to a tile-db similar to one created by, by tile_coverage.py
#REF_TILE_TABLE  - name of table containing  paths to reference tiles
#REF_TILE_NAME_FIELD - name of field containing tile_name (e.g. 1km_6147_545)
#REF_TILE_PATH_FIELD - name of field containing path to ref-tile.
#PROCESS SPECIFIC CONTROLS
#MP=4  #maximal number of processes to spawn - will use qc_wrap default if not defined.
#RUN_ID=None #can be set to a number and passed on to reporting database.
#ADDITIONAL ARGUMENTS TO PASS ON TO TEST:
#TARGS=["-some_argument","and_its_value","-some_other_arg","its_value","-foo","-bar","-layersql","select wkb_geometry from mylayer where ST_Area(wkb_geometry)>0.1"] #or TARGS=[]

class StatusUpdater(object):
    """ Class to call for status updates. Methods in parameter file must accept testname,n_done,n_err,n_alive"""
    def __init__(self,method):
        assert(hasattr(method,"__call__"))
        self.method=method
    def update(self,testname,n_done,n_err,n_alive=None):
        try:
            self.method(testname,n_done,n_err,n_alive)
        except Exception as e:
            print("Update method failed:\n"+str(e))
    
#names that can be defined in parameter file (or on command line):
NAMES={"TESTNAME":str,
"INPUT_TILE_CONNECTION":unicode,
"INPUT_LAYER_SQL":str,  #ExecuteSQL does not like unicode...
"USE_LOCAL":bool,
"SCHEMA":str,
"REF_DATA_CONNECTION":unicode,
"REF_TILE_DB":unicode,
"REF_TILE_TABLE":str,
"REF_TILE_NAME_FIELD":str,
"REF_TILE_PATH_FIELD":str,
"MP":int,
"RUN_ID":int,
"TARGS":list,
"post_execute":StatusUpdater, 
"status_update":StatusUpdater,
"STATUS_INTERVAL":float} 
#Placeholders for testname,n_done and n_exceptions
#names that really must be defined
MUST_BE_DEFINED=["TESTNAME","INPUT_TILE_CONNECTION"]
#DEFAULTS FOR STUFF THATS NOT SPECIFIED (other than None):
DEFAULTS={"USE_LOCAL":False,"REF_TILE_TABLE":"coverage","REF_TILE_NAME_FIELD":"tile_name","REF_TILE_PATH_FIELD":"path","TARGS":[],"STATUS_INTERVAL":3600}
#argument handling - set destination name to correpsond to one of the names in NAMES
parser=argparse.ArgumentParser(description="Wrapper rutine for qc modules. Will use a sqlite database to manage multi-processing.")
parser.add_argument("param_file",help="Input python parameter file.",nargs="?")
parser.add_argument("-testname",dest="TESTNAME",help="Specify testname, will override a definition in parameter file.")
parser.add_argument("-testhelp",help="Just print help for selected test.")
parser.add_argument("-runid",dest="RUN_ID",type=int,help="Specify runid for reporting. Will override a definition in paramater file.")
parser.add_argument("-schema",dest="SCHEMA",help="Specify schema to report into (if relevant) for PostGis db. Will override a definition in parameter file.")
parser.add_argument("-tiles",dest="INPUT_TILE_CONNECTION",help="Specify OGR-connection to tile layer (e.g. mytiles.sqlite). Will override INPUT_TILE_CONNECTION in parameter file.")
parser.add_argument("-tilesql",dest="INPUT_LAYER_SQL",help="Specify SQL to select path from input tile layer.")
parser.add_argument("-targs",dest="TARGS",help="Specify target argument list (as a quoted string) - will override parameter file definition.")
parser.add_argument("-use_local",dest="USE_LOCAL",choices=[0,1],type=int,help="Force using a local spatialite database for reporting (value must be 0 or 1).") #store_true does not work if we want to override a file definition...
parser.add_argument("-mp",dest="MP",type=int,help="Specify maximal number of processes to spawn (defaults to number of kernels).")
parser.add_argument("-statusinterval",dest="STATUS_INTERVAL",help="Specify an interval for which to run status updates (if method is defined in parameter file - default 1 hour).")
group=parser.add_mutually_exclusive_group()
group.add_argument("-refcon",dest="REF_DATA_CONNECTION",help="Specify connection string to (non-tiled) reference data.")
group.add_argument("-reftiles",dest="REF_TILE_DB",help="Specify path to reference tile db")



    


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
            

        
def main(args):
    pargs=parser.parse_args(args[1:])
    if pargs.testhelp is not None:
        #just print some help...
        if not pargs.testhelp in qc.tests:
            print(pargs.testhelp+" not mapped to any test.")
            show_tests()
        else:
            test_usage=qc.usage(pargs.testhelp)
            if test_usage is not None:
                test_usage()
            else:
                print("No usage defined in "+pargs.testhelp)
        return 1
    #Start argument handling with commandline taking precedence...
    args=dict.fromkeys(NAMES.keys(),None)
    args.update(DEFAULTS)
    fargs={"__name__":"qc_wrap"} #a dict holding names from parameter-file - defining __name__ allows for some nice tricks in paramfile.
    if pargs.param_file is not None: #testname is not specified so we use a parameter filr
        fargs["__file__"]=os.path.realpath(pargs.param_file) #if the parameter file wants to know it's own location!
        try:
            execfile(pargs.param_file,fargs) 
        except Exception,e:
            print("Failed to parse parameterfile:\n"+str(e))
            usage(short=True)
        #perhaps validate keys from param-file. However a lot more can be defined there...
    
    #normalise arguments... get the keyes we need with commandline taking precedence
    for key in NAMES.keys():
        val=None
        if key in fargs and fargs[key] is not None:
            val=fargs[key]
        if key in pargs.__dict__ and pargs.__dict__[key] is not None:
            if val is not None:
                print("Overriding "+key+" with command line definition.")
            val=pargs.__dict__[key]
        if val is not None:
            #apply converters
            if key=="TARGS":
                if isinstance(val,str) or isinstance(val,unicode):
                    val=shlex.split(val)
            try:
                val=NAMES[key](val)
            except Exception,e:
                print("Value of "+key+" could not be converted: \n"+str(e))
            if key=="TESTNAME":
                val=os.path.basename(val).replace(".py","")
            args[key]=val
            print("Defining "+key+": "+repr(val))
            
    for key in MUST_BE_DEFINED:
        if args[key] is None:
            print("ERROR: "+key+ " must be defined on command line or in parameter file!!")
            usage(short=True)
    
    if not args["TESTNAME"] in qc.tests:
        print("%s,defined in parameter file, not matched to any test (yet....)" %args["TESTNAME"])
        show_tests()
        return 1
    
    
    #see if test uses ref-data and reference data is defined..
    use_ref_data=qc.tests[args["TESTNAME"]][0]
    use_reporting=qc.tests[args["TESTNAME"]][1]
    ref_data_defined=False
    for key in ["REF_DATA_CONNECTION","REF_TILE_DB"]:
        ref_data_defined|=(args[key] is not None)
    if use_ref_data:
        if not ref_data_defined:
            print("Sorry, "+testname+" uses reference data.\nMust be defined in parameter file in either REF_DATA_CONNECTION or REF_TILE_DB!")
            usage(short=True)
    #import valid arguments from test
    test_parser=qc.get_argument_parser(args["TESTNAME"])
    if len(args["TARGS"])>0: #validate targs
        print("Validating arguments for "+args["TESTNAME"]+"\n")
        if test_parser is not None:
            _targs=["dummy"]
            if use_ref_data:
                _targs.append("dummy")
            _targs.extend(args["TARGS"])
            try:
                test_parser.parse_args(_targs)
            except Exception,e:
                print("Error parsing arguments for test script "+args["TESTNAME"]+":")
                print(str(e))
                return 1
        else:
            print("No argument parser in "+args["TESTNAME"]+" - unable to check arguments to test.")
        
    if use_reporting:
        if args["USE_LOCAL"]:
            #will do nothing if it already exists
            #should be done 'process safe' so that its available for writing for the child processes...
            report.create_local_datasource()
            if args["SCHEMA"] is not None: #mutually exclusive - actually checked by parser...
                print("WARNING: USE_LOCAL is True, local reporting database does not support schema names.")
                print("Will ignore SCHEMA")
        #check the schema arg
        else:
            if args["SCHEMA"] is None:
                print("ERROR: Schema MUST be specified when using a global datasource for reporting!")
                return 1
            print("Schema is set to: "+args["SCHEMA"])
            #Test if we can open the global datasource with given schema
            print("Testing connection to reporting db...")
            layers_defined=report.schema_exists(args["SCHEMA"])
            print("Layers defined: "+str(layers_defined))
            if (not layers_defined):
                print("Creating schema/layers...")
                try:
                    report.create_schema(args["SCHEMA"])
                except Exception,e:
                    print("Failed: "+str(e))
                    return 1
    
        
    #############
    ## Get input tiles#
    #############
    print("Getting tiles from ogr datasource: "+args["INPUT_TILE_CONNECTION"])
    input_files=[]
    #improve by adding a layername
    ds=ogr.Open(args["INPUT_TILE_CONNECTION"])
    if ds is None:
        print("Failed to open input tile layer!")
        return 1
    if args["INPUT_LAYER_SQL"] is not None:
        print("Exceuting SQL to get input paths: "+args["INPUT_LAYER_SQL"])
        layer=ds.ExecuteSQL(str(args["INPUT_LAYER_SQL"]))
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
        if (not remote_files.is_remote(path)) and (not os.path.exists(path)):
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
    if use_ref_data:
        #test wheter we want tiled reference data...
        if args["REF_DATA_CONNECTION"] is not None:
            tiled_ref_data=False
            args["REF_DATA_CONNECTION"]
            print("A non-tiled reference datasource is specified.")
            print("Testing reference data connection....")
            ds=ogr.Open(args["REF_DATA_CONNECTION"])
            if ds is None:
                print("Failed to open reference datasource.")
                return 1
            ds=None
            print("ok...")
            matched_files=[(name,args["REF_DATA_CONNECTION"]) for name in input_files] 
        else:
            tiled_ref_data=True
            print("Tiled reference data specified... getting corresponding tiles.")
            print("Assuming that "+ args["REF_TILE_DB"]+ " has table named "+args["REF_TILE_TABLE"]+" with fields "+args["REF_TILE_NAME_FIELD"]+","+args["REF_TILE_PATH_FIELD"])
            ds=ogr.Open(args["REF_TILE_DB"])
            assert(ds is not None)
            matched_files=[]
            n_not_existing=0
            for name in input_files:
                tile_name=constants.get_tilename(name)
                #Wow - hard to bypass SQL-injection here... ;-()
                layer=ds.ExecuteSQL("select "+args["REF_TILE_PATH_FIELD"]+" from "+args["REF_TILE_TABLE"]+" where "+args["REF_TILE_NAME_FIELD"]+"='{0:s}'".format(tile_name))
                if layer.GetFeatureCount()>1:
                    print("Hmmm - more than one reference tile...")
                if layer.GetFeatureCount()==0:
                    print("Reference tile corresponding to "+name+" not found in db.")
                    n_not_existing+=1
                    continue
                feat=layer[0]
                ref_tile=feat.GetField(0)
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
    testname=args["TESTNAME"] #getting lazy...
    if len(matched_files)>0:
        #Create db for process control...
        lock=multiprocessing.Lock()
        db_name=create_process_db(testname,matched_files)
        if db_name is None:
            print("Something wrong - process control db not created.")
            return 1
        if args["MP"] is not None:
            mp=args["MP"]
        else:
            mp=multiprocessing.cpu_count()
        assert(mp>0)
        n_tasks=min(mp,len(matched_files))
        print("Starting %d process(es)." %n_tasks)
        if args["RUN_ID"] is not None:
            print("Run-id is set to: %d" %args["RUN_ID"])
        print("Using process db: "+db_name)
        tasks=[]
        for i in range(n_tasks):
            p = multiprocessing.Process(target=run_check, args=(i,testname,db_name,args["TARGS"],args["RUN_ID"],args["USE_LOCAL"],args["SCHEMA"],use_ref_data,lock))
            tasks.append(p)
            p.start()
        #Now watch the processing#
        con=sqlite3.connect(db_name)
        cur=con.cursor()
        n_todo=len(matched_files)
        n_crashes=0
        n_done=0
        n_err=0
        n_left=n_todo
        n_alive=n_tasks
        #start clock#
        t1=time.time()  #we don't wanne measure cpu-time here...
        t_last_report=0
        t_last_status=t1
        
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
            now=time.time()
            dt=now-t1
            dt_last_report=now-t_last_report
            dt_last_status=now-t_last_status
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
                if args["status_update"] is not None and dt_last_status>args["STATUS_INTERVAL"]:
                    args["status_update"].update(args["TESTNAME"],n_done,n_err,n_alive)
                    t_last_status=now
            #Try to keep n_tasks alive... If n_left>n_alive, which means that there could be some with status 0 still left...
            if n_alive<n_tasks and n_left>n_alive:
                print("[qc_wrap]: A process seems to have stopped...")
                n_crashes+=1
        t2=time.time()
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
    if args["post_execute"] is not None:
        args["post_execute"].update(args["TESTNAME"],n_done,n_err,n_alive)
    return (n_err+n_crashes)
    

if __name__=="__main__":
    main(sys.argv)
    