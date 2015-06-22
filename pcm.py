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
import logging
from qc import dhmqc_constants as constants
from qc.utils import osutils  
import qc
import sqlite3 as db
import argparse 
import platform
import random
import glob


PROC_TABLE="proc_jobs"
SCRIPT_TABLE="proc_scripts"


LOGDIR=os.path.join(os.path.dirname(__file__),"logs")

STATUS_PROCESSING=1
STATUS_OK=2
STATUS_ERROR=3

#SQL to create a local sqlite db - should be readable by ogr...
CREATE_PROC_TABLE="CREATE TABLE proc_jobs(id INTEGER PRIMARY KEY, wkt_geometry TEXT, tile_name TEXT, path TEXT, script_id INTEGER, exe_start TEXT, exe_end TEXT, status INTEGER, rcode INTEGER, msg TEXT, client TEXT)"
CREATE_SCRIPT_TABLE="CREATE TABLE proc_scripts(id INTEGER PRIMARY KEY,code TEXT)"



#argument handling - set destination name to correpsond to one of the names in NAMES
parser=argparse.ArgumentParser(description="Processing client which will listen for jobs in a database. OR push jobs to the database...")
subparsers = parser.add_subparsers(help="sub-command help",dest="mode")
parser_push = subparsers.add_parser("push", help="push help", description="Push jobs to db.")
parser_push.add_argument("cstr",help="Connection string to db.")
parser_push.add_argument("files",help="Glob pattern for paths (should be an ogr-layer)")
script_group=parser_push.add_mutually_exclusive_group(required=True)
script_group.add_argument("-script",help="Path to job definition script.")
script_group.add_argument("-script_id",help="id of already existing row in script table.",type=int)
parser_create = subparsers.add_parser("create", help="create help", description="Create processing tables in a db.")
parser_create.add_argument("cstr",help="Connetion string to db.")
parser_work= subparsers.add_parser("work", help="work help", description="Volunteer for some work.")
parser_work.add_argument("cstr",help="Connection string to processing db.")
parser_work.add_argument("-n",dest="MP",type=int,help="Specify maximal number of processes to spawn (defaults to number of kernels).")
parser_info = subparsers.add_parser("info", help="info help", description="Show some info for the processeing tables.")
parser_info.add_argument("cstr",help="Connection string to db.")
parser_update=subparsers.add_parser("update", help="update help", description="Execute a sql command on the processing tables.")
parser_update.add_argument("cstr",help="Connection string to db.")
parser_update.add_argument("sql",help="Execute a sql request.")
parser_scripts=subparsers.add_parser("scripts", help="scripts help", description="Show defined scripts.")
parser_scripts.add_argument("cstr",help="Connetion string to db.")


def create_tables(cstr):
    con=db.connect(cstr)
    cur=con.cursor()
    cur.execute(CREATE_PROC_TABLE)
    cur.execute(CREATE_SCRIPT_TABLE)
    con.commit()
    cur.close()
    con.close()
    

def push_job(files,cstr,path_script=None,script_id=None):
    con=db.connect(cstr)
    cur=con.cursor()
    if path_script is not None:
        with open(path_script,"r") as f:
            src=f.read()
        cur.execute("insert into proc_scripts(code) values(?)",(src,))
        id=cur.lastrowid
    else:
        assert(script_id is not None)
        id=script_id
        cur.execute("select code from proc_scripts where id=?",(id,))
        data=cur.fetchone()
        if data is None:
            raise Exception("That script_id did not exist!")
        src=data[0]
    print("Pushing jobs using code:")
    print(src)
    n_added=0
    for name in files:
        tile=constants.get_tilename(name)
        wkt=constants.tilename_to_extent(tile,return_wkt=True)
        cur.execute("insert into proc_jobs(wkt_geometry,tile_name,path,script_id,status) values(?,?,?,?,?)",(wkt,tile,name,id,0))
        n_added+=1
    print("Inserted %d rows." %n_added)
    con.commit()
    cur.close()
    con.close()

def get_info(cstr,full=False,worker=None):
    con=db.connect(cstr)
    cur=con.cursor()
    n_done=0
    n_scripts=0
    n_err=0
    cur.execute("select count() from proc_jobs where status=?",(STATUS_PROCESSING,))
    n_proc=cur.fetchone()[0]
    cur.execute("select count() from proc_jobs where status=0")
    n_todo=cur.fetchone()[0]
    if full:
        cur.execute("select count() from proc_jobs where status=?",(STATUS_OK,))
        n_done=cur.fetchone()[0]
        cur.execute("select count() from proc_jobs where status=?",(STATUS_ERROR,))
        n_err=cur.fetchone()[0]
        cur.execute("select count() from proc_scripts")
        n_scripts=cur.fetchone()[0]
    return n_todo,n_proc,n_done,n_err,n_scripts

def show_scripts(cstr,limit=None):
    con=db.connect(cstr)
    cur=con.cursor()
    cur.execute("select id,code from proc_scripts")
    data=cur.fetchall()
    for row in data:
        print("ID: %d\ncode:\n%s\n"%(row[0],row[1]))
    cur.close()
    con.close()
    

def update_tables(cstr,sql):
    con=db.connect(cstr)
    cur=con.cursor()
    print("Executing "+sql)
    cur.execute(sql)
    con.commit()
    data=cur.fetchone()
    if data is not None:
        print(str(data))
    cur.execute("select total_changes() from proc_jobs")
    n_changed=cur.fetchone()[0]
    print("Changed rows in job table: %d" %n_changed)
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
        time.sleep(4+random.random()*2)
        cur.execute("select id,path,script_id from proc_jobs where status=0 limit 1")
        task=cur.fetchone()
        if task is None:
            continue
        fid,path,script_id=task
        cur.execute("update proc_jobs set status=?, client=? where id=?",(STATUS_PROCESSING,client,fid))
        con.commit()
        cur.execute("select code from proc_scripts where id=?",(script_id,))
        data=cur.fetchone()
        if data is None:
            logger.error("Could not select code from id: %d" %fid)
            cur.execute("update proc_jobs set status=?,msg=? where id=?",(STATUS_ERROR,"Script id did not exist.",fid))
            con.commit()
            continue
        src=data[0] #hmmm - encoding
        logger.info("Was told to do code with id %d on data %s" %(script_id,path))
        
        #now just run the script.... hmm - perhaps import with importlib and run it??
        stdout.write(sl+"[proc_client] Doing script_id %s from %s"%(script_id,db_cstr))
        args={"__name__":"qc_wrap","path":path}
        try:
            code=compile(src,"<string>","exec")
            eval(code,args)
        except Exception,e:
            stderr.write("[proc_client]: Exception caught:\n"+msg+"\n")
            stderr.write("[proc_client]: Traceback:\n"+traceback.format_exc()+"\n")
            logger.error("Caught: \n"+str(e))
            cur.execute("update proc_jobs set status=?,msg=? where id=?",(STATUS_ERROR,str(e),fid))
            con.commit()
        else:
            cur.execute("update proc_jobs set status=?,msg=? where id=?",(STATUS_OK,"OK",fid))
            con.commit()
        
 
                

        
def main(args):
    pargs=parser.parse_args(args[1:])
    if pargs.mode=="create":
        create_tables(pargs.cstr)
        return
    if pargs.mode=="push":
        files=glob.glob(pargs.files)
        push_job(files,pargs.cstr,pargs.script,pargs.script_id)
        return
    if pargs.mode=="info":
        n_todo,n_proc,n_done,n_err,n_scripts=get_info(pargs.cstr,full=True)
        print("INFO for "+pargs.cstr)
        print("Open jobs      : %d" %n_todo)
        print("Active jobs    : %d"%n_proc)
        print("Finished jobs  : %d"%n_done)
        print("Exceptions     : %d"%n_err)
        print("Scripts defined: %d" %n_scripts)
        return
    if pargs.mode=="update":
        update_tables(pargs.cstr,pargs.sql)
        return
    if pargs.mode=="scripts":
        show_scripts(pargs.cstr)
        return
    assert(pargs.mode=="work")
    #start a pool of worker processes
    print("Starting a pool of %d workers." %(pargs.MP,))
    workers=[]
    if pargs.MP is None:
        pargs.MP=multiprocessing.cpu_count()
    lock=multiprocessing.Lock()
    for i in range(pargs.MP):
        p = multiprocessing.Process(target=proc_client, args=(i,pargs.cstr,lock))
        workers.append(p)
        p.start()
    #Now watch the processing#
    n_alive=len(workers)
    #start clock#
    t1=time.clock()
    t_last_report=0
    t_last_status=t1
    while n_alive>0:
        time.sleep(5)
        n_alive=0
        for p in workers:
            n_alive+=p.is_alive()
        now=time.clock()
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
    