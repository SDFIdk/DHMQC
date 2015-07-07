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
import sys,os,time
import traceback
import multiprocessing 
import logging
import qc
from qc.db import report
from qc import dhmqc_constants as constants
from qc.utils import osutils  
import psycopg2 as db
import platform
import random
import json


PROC_TABLE="proc_jobs"
SCRIPT_TABLE="proc_scripts"


LOGDIR=os.path.join(os.path.dirname(__file__),"logs")

STATUS_PROCESSING=1
STATUS_OK=2
STATUS_ERROR=3

#SQL to create a local sqlite db - should be readable by ogr...
#CREATE_PROC_TABLE="""
#CREATE TABLE proc_jobs(id INTEGER PRIMARY KEY, wkt_geometry TEXT,
#tile_name TEXT, path TEXT, script TEXT, exe_start TEXT, exe_end TEXT, 
#status INTEGER, rcode INTEGER, msg TEXT, client TEXT, priority INTEGER, version INTEGER)"""
#CREATE_SCRIPT_TABLE="CREATE TABLE proc_scripts(id INTEGER PRIMARY KEY, name TEXT UNIQUE, code TEXT)"

def proc_client(p_number,db_cstr,lock):
    #The processing client which should be importable from all processes.
    client=platform.node()+":%d"%p_number
    logger = multiprocessing.log_to_stderr()
    logger.setLevel(logging.INFO)
    try:
        con=db.connect(db_cstr)
        cur=con.cursor()
    except Exception,e:
        logger.error("Unable to connect db:\n"+str(e))
        return #stop
    time.sleep(2+random.random()*2)
    logger.info("I'm ready - listening for stuff to do.")
    logname="proc_client_"+(time.asctime().split()[-2]).replace(":","_")+"_"+str(p_number)+".log"
    logname=os.path.join(LOGDIR,logname)
    logfile=open(logname,"w")
    stdout=osutils.redirect_stdout(logfile)
    stderr=osutils.redirect_stderr(logfile)
    sl="*-*"*23+"\n"
    stdout.write(sl+"Process %d is listening.\n"%p_number+sl)
    alive=True
    while alive:
        time.sleep(random.random()*2)
        cur.execute("select ogc_fid,path,ref_cstr,job_id,version from proc_jobs where status=0 order by priority desc limit 1")
        task=cur.fetchone()
        if task is None:
            continue
        id,path,ref_path,job_id,version=task
        logger.info("version was: %d" %version)
        cur.execute("update proc_jobs set status=%s, client=%s, version=%s, exe_start=clock_timestamp() where ogc_fid=%s and version=%s",(STATUS_PROCESSING,client,version+1,id,version))
        if cur.rowcount!=1:
            logger.warning("Failed to grab a row - probably a concurrency issue.")
            continue
        con.commit()
        cur.execute("select testname,report_schema,run_id,targs from proc_defs where id=%s",(job_id,))
        data=cur.fetchone()
        if data is None:
            logger.error("Could not select definition with id: %s" %job_id)
            cur.execute("update proc_jobs set status=%s,msg=%s where ogc_fid=%s",(STATUS_ERROR,"Definition did not exist.",id))
            con.commit()
            continue
        testname,schema,runid,targs=data
        logger.info("Was told to do job with id %s, test %s, on data (%s,%s)" %(job_id,testname,path,ref_path))
        #now just run the script.... hmm - perhaps import with importlib and run it??
        stdout.write(sl+"[proc_client] Doing definition %s from %s, test: %s\n"%(job_id,db_cstr,testname))
        args={"__name__":"qc_wrap","path":path}
        try: 
            targs=json.loads(targs) #convert to a python list
            test_func=qc.get_test(testname)
            use_ref_data=qc.tests[testname][0]
            use_reporting=qc.tests[testname][1]
            #both of these can be None - but that's ok.
            if use_reporting:
                report.set_run_id(runid)
                report.set_schema(schema)
            send_args=[testname,path]
            if use_ref_data:
                assert(len(ref_path)>0)
                send_args.append(ref_path)
            send_args+=targs
            rc=test_func(send_args)
            
        except Exception,e:
            stderr.write("[proc_client]: Exception caught:\n"+str(e)+"\n")
            stderr.write("[proc_client]: Traceback:\n"+traceback.format_exc()+"\n")
            logger.error("Caught: \n"+str(e))
            msg=str(e)[:128] #truncate msg for now - or use larger field width.
            cur.execute("update proc_jobs set status=%s,msg=%s where ogc_fid=%s",(STATUS_ERROR,msg,id))
            con.commit()
        else:
            cur.execute("update proc_jobs set status=%s,rcode=%s,msg=%s,exe_end=clock_timestamp() where ogc_fid=%s",(STATUS_OK,rc,"OK",id))
            con.commit()




if __name__=="__main__":
    from proc_setup import *
    import argparse 
    #argument handling - set destination name to correpsond to one of the names in NAMES
    parser=argparse.ArgumentParser(description="Processing client which will listen for jobs in a database. OR push jobs to the database...")
    subparsers = parser.add_subparsers(help="sub-command help",dest="mode")
    #push
    parser_push = subparsers.add_parser("push", help="push help", description="Push jobs to db.")
    parser_push.add_argument("cstr",help="Connection string to processing db.")
    parser_push.add_argument("param_file",help="Input python parameter file.",nargs="?")
    parser_push.add_argument("-testname",dest="TESTNAME",help="Specify testname, will override a definition in parameter file.")
    parser_push.add_argument("-runid",dest="RUN_ID",type=int,help="Specify runid for reporting. Will override a definition in paramater file.")
    parser_push.add_argument("-schema",dest="SCHEMA",help="Specify schema to report into (if relevant) for PostGis db. Will override a definition in parameter file.")
    parser_push.add_argument("-tiles",dest="INPUT_TILE_CONNECTION",help="Specify OGR-connection to tile layer (e.g. mytiles.sqlite). Will override INPUT_TILE_CONNECTION in parameter file.")
    parser_push.add_argument("-tilesql",dest="INPUT_LAYER_SQL",help="Specify SQL to select path from input tile layer.")
    parser_push.add_argument("-targs",dest="TARGS",help="Specify target argument list (as a quoted string) - will override parameter file definition.")
    parser_push.add_argument("-priority",dest="PRIORITY",type=int,help="Priority of job (0->??).")
    push_group=parser.add_mutually_exclusive_group()
    push_group.add_argument("-refcon",dest="REF_DATA_CONNECTION",help="Specify connection string to (non-tiled) reference data.")
    push_group.add_argument("-reftiles",dest="REF_TILE_DB",help="Specify path to reference tile db")
    #create
    parser_create = subparsers.add_parser("create", help="create help", description="Create processing tables in a db.")
    parser_create.add_argument("cstr",help="Connetion string to db.")
    parser_create.add_argument("-drop",help="Drop processing tables.",action="store_true")
    #work
    parser_work= subparsers.add_parser("work", help="work help", description="Volunteer for some work.")
    parser_work.add_argument("cstr",help="Connection string to processing db.")
    parser_work.add_argument("-n",dest="MP",type=int,help="Specify maximal number of processes to spawn (defaults to number of kernels).")
    #info
    parser_info = subparsers.add_parser("info", help="info help", description="Show some info for the processeing tables.")
    parser_info.add_argument("cstr",help="Connection string to db.")
    #update
    parser_update=subparsers.add_parser("update", help="update help", description="Execute a sql command on the processing tables.")
    parser_update.add_argument("cstr",help="Connection string to db.")
    parser_update.add_argument("sql",help="Execute a sql request.")
    #scripts
    parser_scripts=subparsers.add_parser("defs", help="Definitions help", description="Show defined tasks.")
    parser_scripts.add_argument("cstr",help="Connetion string to db.")
    
    
    CREATE_POSTGRES_TABLES="""
    CREATE TABLE proc_defs(id serial PRIMARY KEY, testname character varying(32), report_schema character varying(64), run_id integer, targs text, n_tiles integer, created_time timestamp, created_by character varying(32));
    CREATE TABLE proc_jobs(ogc_fid serial PRIMARY KEY, tile_name character varying(15), path character varying(128), ref_cstr character varying(128),
    job_id integer REFERENCES proc_defs(id) ON DELETE RESTRICT, exe_start timestamp, exe_end timestamp, 
    status smallint, rcode smallint, msg character varying(128), 
    client character varying(32), 
    priority smallint, version smallint);
    SELECT AddGeometryColumn('proc_jobs','wkb_geometry',25832,'POLYGON',2);
    CREATE INDEX proc_jobs_geom_idx
      ON proc_jobs
      USING gist
      (wkb_geometry);
    CREATE INDEX proc_jobs_status_idx
      ON proc_jobs(status);
    """
   

    def create_tables(cstr):
        con=db.connect(cstr)
        cur=con.cursor()
        cur.execute(CREATE_POSTGRES_TABLES)
        con.commit()
        cur.close()
        con.close()
        print("Successfully created processing tables in "+cstr)
    
    def drop_tables(cstr):
        areyousure=raw_input("Are you really, really sure you wanna drop tables and kill all clients? [YES/no]:")
        if areyousure.strip()=="YES":
            print("OK - you told me to do it!")
            con=db.connect(cstr)
            cur=con.cursor()
            cur.execute("DROP TABLE IF EXISTS proc_jobs")
            cur.execute("DROP TABLE IF EXISTS proc_defs")
            con.commit()
            
        
   
    def push_job(cstr,matched_files,job_def):
        #very similar to stuff in qc_wrap
        con=db.connect(cstr)
        cur=con.cursor()
        testname=job_def["TESTNAME"]
        targs=json.dumps(job_def["TARGS"])
        runid=job_def["RUN_ID"]
        schema=job_def["SCHEMA"]
        priority=job_def["PRIORITY"]
        client=platform.node()
        n_tiles=len(matched_files)
        cur.execute("insert into proc_defs(testname,report_schema,run_id,targs,n_tiles,created_time,created_by) values(%s,%s,%s,%s,%s,now(),%s) returning id",(testname,schema,runid,targs,n_tiles,client))
        job_id= cur.fetchone()[0]
        n_added=0
        #Now add a row in job_def table
        for tile_path,ref_path in matched_files:
            try: #or use ogr-geometry
                tile=constants.get_tilename(tile_path)
                wkt=constants.tilename_to_extent(tile,return_wkt=True)
            except Exception,e:
                print("Bad tilename in "+tile_path)
                continue
            cur.execute("insert into proc_jobs(wkb_geometry,tile_name,path,ref_cstr,job_id,status,priority,version) values(st_geomfromtext(%s,25832),%s,%s,%s,%s,%s,%s,%s)",(wkt,tile,tile_path,ref_path,job_id,0,priority,0))
            n_added+=1
        print("Inserted %d rows." %n_added)
        con.commit()
        cur.close()
        con.close()

    def get_info(cstr,full=False,worker=None):
        con=db.connect(cstr)
        cur=con.cursor()
        n_done=0
        n_defs=0
        n_err=0
        cur.execute("select count(*) from proc_jobs where status=%s",(STATUS_PROCESSING,))
        n_proc=cur.fetchone()[0]
        cur.execute("select count(*) from proc_jobs where status=0")
        n_todo=cur.fetchone()[0]
        if full:
            cur.execute("select count(*) from proc_jobs where status=%s",(STATUS_OK,))
            n_done=cur.fetchone()[0]
            cur.execute("select count(*) from proc_jobs where status=%s",(STATUS_ERROR,))
            n_err=cur.fetchone()[0]
            cur.execute("select count(*) from proc_defs")
            n_defs=cur.fetchone()[0]
        return n_todo,n_proc,n_done,n_err,n_defs

    def show_defs(cstr,limit=None):
        con=db.connect(cstr)
        cur=con.cursor()
        cur.execute("select * from proc_defs")
        data=cur.fetchall()
        sl="*"*50
        print("There were %d definition(s) in defs table." %len(data))
        print(sl)
        fmt="{0:<3s} {1:<16s} {2:<12s} {3:<8s} {4:<8s} {5:<24s} {6:<12s}"
        for row in data:
            print(fmt.format("id","testname","schema","runid","n_tiles","created at","created by"))
            print(fmt.format(str(row[0]),row[1],row[2],str(row[3]),str(row[5]),row[6].strftime("%Y-%m-%d %H:%M:%S"),row[7]))
            print("targs:")
            print(row[4])
            print(sl)
        cur.close()
        con.close()
        

    def update_tables(cstr,sql):
        con=db.connect(cstr)
        cur=con.cursor()
        print("Executing: "+sql)
        cur.execute(sql)
        n_changed=cur.rowcount
        con.commit()
        print("Affected rows in job table: %d" %n_changed)
        cur.close()
        con.close()
        

def main(args):
    pargs=parser.parse_args(args[1:])
    if pargs.mode=="create":
        if pargs.drop:
            drop_tables(pargs.cstr)
        else:
            create_tables(pargs.cstr)
        return
    if pargs.mode=="push":
        rc,matched_files,args=setup_job(PCM_NAMES,PCM_DEFAULTS,pargs.__dict__,pargs.param_file)
        if rc!=0:
            #something went wrong - msg. should have been displayed
            return 
        push_job(pargs.cstr,matched_files,args)
        return
    if pargs.mode=="info":
        n_todo,n_proc,n_done,n_err,n_defs=get_info(pargs.cstr,full=True)
        print("INFO for "+pargs.cstr)
        print("Open jobs      : %d" %n_todo)
        print("Active jobs    : %d"%n_proc)
        print("Finished jobs  : %d"%n_done)
        print("Exceptions     : %d"%n_err)
        print("Job definitions: %d" %n_defs)
        return
    if pargs.mode=="update":
        update_tables(pargs.cstr,pargs.sql)
        return
    if pargs.mode=="defs":
       show_defs(pargs.cstr)
       return
    assert(pargs.mode=="work")
    #start a pool of worker processes
    if pargs.MP is None:
        pargs.MP=multiprocessing.cpu_count()
    print("Starting a pool of %d workers." %(pargs.MP,))
    workers=[]
    lock=multiprocessing.Lock()
    for i in range(pargs.MP):
        p = multiprocessing.Process(target=proc_client, args=(i,pargs.cstr,lock))
        workers.append(p)
        p.start()
    #Now watch the processing#
    n_alive=len(workers)
    #start clock#
    t1=time.time()
    t_last_report=0
    t_last_status=t1
    while n_alive>0:
        time.sleep(5)
        n_alive=0
        for p in workers:
            n_alive+=p.is_alive()
        now=time.time()
        dt=now-t1
        dt_last_report=now-t_last_report
        if dt_last_report>15:
            n_todo,n_proc,n_done,n_err,n_scripts=get_info(pargs.cstr,full=False)
            print("[proc_client]: Open jobs: %d, active jobs: %d, active/listening processes here: %d" %(n_todo,n_proc,n_alive))
            if n_err>0:
                print("[proc_client]: {0:d} exceptions caught.".format(n_err))
            t_last_report=now
  
        
        
    
    

if __name__=="__main__":
    main(sys.argv)
    