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
from osgeo import ogr
from qc import dhmqc_constants as constants
from qc.utils import osutils  

import qc
#import sqlite3 as db
import psycopg2 as db
import argparse 
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

CREATE_JOB_TABLE="""
CREATE TABLE proc_jobs(ogc_fid serial PRIMARY KEY, tile_name character varying(15), path character varying(128), ref_cstr character varying(128),
job_name character varying(32), exe_start timestamp, exe_end timestamp, 
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
CREATE_DEF_TABLE="""
CREATE TABLE proc_defs(id serial PRIMARY KEY, job_name character varying(32) UNIQUE, json_def text)
"""




if __name__=="__main__":
    #argument handling - set destination name to correpsond to one of the names in NAMES
    parser=argparse.ArgumentParser(description="Processing client which will listen for jobs in a database. OR push jobs to the database...")
    subparsers = parser.add_subparsers(help="sub-command help",dest="mode")
    #push
    parser_push = subparsers.add_parser("push", help="push help", description="Push jobs to db.")
    parser_push.add_argument("cstr",help="Connection string to processing db.")
    parser_push.add_argument("tiles",help="OGR-connection string to tile db.")
    parser_push.add_argument("tilesql",help="sql to select path attr from tile layer.")
    parser_push.add_argument("job_name",help="Name of already defined json-definition in definitions table.")
    #create
    parser_create = subparsers.add_parser("create", help="create help", description="Create processing tables in a db.")
    parser_create.add_argument("cstr",help="Connetion string to db.")
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
    group_scripts=parser_scripts.add_mutually_exclusive_group(required=True)
    group_scripts.add_argument("-push",help="Path to new json-definition to push onto definition table (basename must be unique).")
    group_scripts.add_argument("-show",action="store_true",help="Show already defined definitions.")
    


    def create_tables(cstr):
        con=db.connect(cstr)
        cur=con.cursor()
        cur.execute(CREATE_JOB_TABLE)
        cur.execute(CREATE_DEF_TABLE)
        con.commit()
        cur.close()
        con.close()
        
    def push_def(cstr,path):
        con=db.connect(cstr)
        cur=con.cursor()
        assert(os.path.splitext(path)[1]==".json")
        with open(path,"r") as f:
                src=f.read()
        assert(len(src)>0)
        try:
            obj=json.loads(src)
        except Exception,e:
            print("Failed to parse definition!!")
            raise e
        name=os.path.splitext(os.path.basename(path))[1]
        try:
            cur.execute("insert into proc_defs(job_name,json_def) values(%s,%s)",(name,src,))
        except Exception,e:
            print("Insertion of definition failed, note: basename must be unique!\n"+str(e))
        else:
            print("Inserted script with name: "+name)
            con.commit()
        
    def push_job(tile_db,tile_sql,cstr,job_name,priority=0):
        con=db.connect(cstr)
        cur=con.cursor()
        job_name=job_name.strip()
        cur.execute("select json_def from proc_defs where job_name=%s",(job_name,))
        data=cur.fetchone()
        if data is None:
            raise Exception("No json_def by name: "+job_name)
        json_def=data[0]
        print("Pushing jobs using definition:\n"+json_def)
        n_added=0
        ds=ogr.Open(tile_db)
        tile_layer=ds.ExecuteSQL(tile_sql)
        print("%d features in tile layer from %s" %(tile_layer.GetFeatureCount(),tile_sql))
        for feat in tile_layer:
            path=feat.GetFieldAsString(0) 
            try: #or use ogr-geometry
                tile=constants.get_tilename(path)
                wkt=constants.tilename_to_extent(tile,return_wkt=True)
            except Exception,e:
                print("Bad tilename in "+path)
                continue
            cur.execute("insert into proc_jobs(wkb_geometry,tile_name,path,job_name,status,priority,version) values(st_geomfromtext(%s,25832),%s,%s,%s,%s,%s,%s)",(wkt,tile,path,job_name,0,priority,0))
            n_added+=1
        print("Inserted %d rows." %n_added)
        ds.ReleaseResultSet(tile_layer)
        con.commit()
        tile_layer=None
        ds=None
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
        cur.execute("select id,job_name,json_def from proc_defs")
        data=cur.fetchall()
        print("There were %d definitions in defs table." %len(data))
        for row in data:
            print("Name:%s id: %d\njson:\n%s\n"%(row[1],row[0],row[2]))
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
        
    def usage(short=False):
        parser.print_help()
        sys.exit(1)






def proc_client(p_number,db_cstr,lock):
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
        cur.execute("select ogc_fid,path,job_name,version from proc_jobs where status=0 order by priority desc limit 1")
        task=cur.fetchone()
        if task is None:
            continue
        id,path,job_name,version=task
        logger.info("version was: %d" %version)
        cur.execute("update proc_jobs set status=%s, client=%s, version=%s, exe_start=now() where ogc_fid=%s and version=%s",(STATUS_PROCESSING,client,version+1,id,version))
        if cur.rowcount!=1:
            logger.warning("Failed to grab a row - probably a concurrency issue.")
            continue
        con.commit()
        cur.execute("select json_def from proc_defs where job_name=%s",(job_name,))
        data=cur.fetchone()
        if data is None:
            logger.error("Could not select definition with name: %s" %job_name)
            cur.execute("update proc_jobs set status=%s,msg=%s where ogc_fid=%s",(STATUS_ERROR,"Script did not exist.",id))
            con.commit()
            continue
        json_def=data[0] #hmmm - encoding
        logger.info("Was told to do job with name %s on data %s" %(job_name,path))
        
        #now just run the script.... hmm - perhaps import with importlib and run it??
        stdout.write(sl+"[proc_client] Doing definition %s from %s"%(job_name,db_cstr))
        args={"__name__":"qc_wrap","path":path}
        try: #dryrun for now - just parse the definition
            obj=json.loads(json_def)
        except Exception,e:
            stderr.write("[proc_client]: Exception caught:\n"+str(e)+"\n")
            stderr.write("[proc_client]: Traceback:\n"+traceback.format_exc()+"\n")
            logger.error("Caught: \n"+str(e))
            cur.execute("update proc_jobs set status=%s,msg=%s where ogc_fid=%s",(STATUS_ERROR,str(e),id))
            con.commit()
        else:
            logger.info("Hmmm - should do something here. For now just sleep...")
            time.sleep(random.random()*10)
            cur.execute("update proc_jobs set status=%s,msg=%s,exe_end=now() where ogc_fid=%s",(STATUS_OK,"OK",id))
            con.commit()
        
 
                

        
def main(args):
    pargs=parser.parse_args(args[1:])
    if pargs.mode=="create":
        create_tables(pargs.cstr)
        return
    if pargs.mode=="push":
        push_job(pargs.tiles,pargs.tilesql,pargs.cstr,pargs.job_name)
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
        if pargs.show:
            show_defs(pargs.cstr)
        else:
            assert(pargs.push is not None)
            push_def(pargs.cstr,pargs.push)
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
    