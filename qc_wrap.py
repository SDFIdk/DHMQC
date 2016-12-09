# Copyright (c) 2015-2016, Danish Geodata Agency <gst@gst.dk>
# Copyright (c) 2016, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
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
'''
qc_wrap.py

Parallelization wrapper for tests in DHMQC
'''

from __future__ import print_function

import sys
import os
import time
import traceback
import multiprocessing
from pyspatialite import dbapi2 as spatialite
import argparse
from datetime import timedelta

from proc_setup import setup_job
from proc_setup import show_tests
from proc_setup import QC_WRAP_NAMES
from proc_setup import QC_WRAP_DEFAULTS
import qc
from qc.db import report
from qc import dhmqc_constants as constants
from qc.utils import osutils

LOGDIR = os.path.join(os.path.dirname(__file__), "logs")
STATUS_PROCESSING = 1
STATUS_OK = 2
STATUS_ERROR = 3



def run_check(p_number, testname, db_name, add_args, runid, use_local, schema, use_ref_data, lock):
    '''
    Main checker rutine which should be defined for all processes.
    '''

    logger = multiprocessing.log_to_stderr()
    test_func = qc.get_test(testname)
    #Set up some globals in various modules... per process.
    if runid is not None:
        report.set_run_id(runid)

    if use_local:
        # rather than sending args to scripts, which might not have implemented
        # handling that particular argument, set a global attr in report.
        report.set_use_local(True)
    elif schema is not None:
        report.set_schema(schema)
    #LOAD THE DATABASE
    con = spatialite.connect(db_name)
    if con is None:
        logger.error("[qc_wrap]: Process: {0:d}, unable to fetch process db".format(p_number))
        return

    cur = con.cursor()
    timestamp = (time.asctime().split()[-2]).replace(':', '_')
    logname = testname + '_' + timestamp + '_' + str(p_number) + '.log'
    logname = os.path.join(LOGDIR, logname)
    logfile = open(logname, 'w')
    stdout = osutils.redirect_stdout(logfile)
    stderr = osutils.redirect_stderr(logfile)
    filler = '*-*' * 23
    print(filler)
    print('[qc_wrap]: Running {test} routine at {time}, process: {proc}, run id: {rid}'.format(
        test=testname,
        time=time.asctime(),
        proc=p_number,
        rid=runid))

    print(filler)
    done = 0
    cur.execute('select count() from ' + testname + ' where status=0')
    n_left = cur.fetchone()[0]
    while n_left > 0:
        print(filler)
        print("[qc_wrap]: Number of tiles left: {0:d}".format(n_left))
        print(filler)
        #Critical section#
        lock.acquire()
        cur.execute("select id,las_path,ref_path from " + testname + " where status=0")
        data = cur.fetchone()
        if data is None:
            print("[qc_wrap]: odd - seems to be no more tiles left...")
            lock.release()
            break
        fid, lasname, vname = data
        cur.execute("update " + testname + " set status=?,prc_id=?,exe_start=? where id=?",
                    (STATUS_PROCESSING, p_number, time.asctime(), fid))
        try:
            con.commit()
        except Exception, err_msg:
            stderr.write("[qc_wrap]: Unable to update tile to finish status...\n" + err_msg + "\n")
            break
        finally:
            lock.release()

        #end critical section#
        print("[qc_wrap]: Doing lasfile {0:s}...".format(lasname))
        send_args = [testname, lasname]
        if use_ref_data:
            send_args.append(vname)
        send_args += add_args
        try:
            return_code = test_func(send_args)
        except Exception, err_msg:
            return_code = -1
            msg = str(err_msg)
            status = STATUS_ERROR
            stderr.write("[qc_wrap]: Exception caught:\n" + msg + "\n")
            stderr.write("[qc_wrap]: Traceback:\n" + traceback.format_exc() + "\n")
        else:
            #set new status
            msg = "ok"
            status = STATUS_OK
            try:
                return_code = int(return_code)
            except (NameError, ValueError):
                return_code = 0
        cur.execute("update " + testname + " set status=?,exe_end=?,rcode=?,msg=? where id=?",
                    (status, time.asctime(), return_code, msg, fid))
        done += 1
        try:
            con.commit()
        except Exception, err_msg:
            stderr.write("[qc_wrap]: Unable to update tile to finish status...\n" + err_msg + "\n")
        #go on to next one...
        cur.execute("select count() from " + testname + " where status=0")
        n_left = cur.fetchone()[0]

    print("[qc_wrap]: Checked %d tiles, finished at %s" %(done, time.asctime()))
    cur.close()
    con.close()
    #avoid writing to a closed fp...
    stdout.close()
    stderr.close()
    logfile.close()


#argument handling - set destination name to correpsond to one of the names in NAMES
parser = argparse.ArgumentParser(
    description='''Wrapper rutine for qc modules. Will use a sqlite database to manage
                   multi-processing.''')
parser.add_argument(
    "param_file",
    help="Input python parameter file.",
    nargs="?")
parser.add_argument(
    "-testname",
    dest="TESTNAME",
    help="Specify testname, will override a definition in parameter file.")
parser.add_argument(
    "-testhelp",
    help="Just print help for selected test.")
parser.add_argument(
    "-runid",
    dest="RUN_ID",
    type=int,
    help="Specify runid for reporting. Will override a definition in paramater file.")
parser.add_argument(
    "-schema",
    dest="SCHEMA",
    help='''Specify schema to report into (if relevant) for PostGis db.
            Will override a definition in parameter file.''')
parser.add_argument(
    '-tiles',
    dest="INPUT_TILE_CONNECTION",
    help='''Specify OGR-connection to tile layer (e.g. mytiles.sqlite).
            Will override INPUT_TILE_CONNECTION in parameter file.''')
parser.add_argument(
    "-tilesql",
    dest="INPUT_LAYER_SQL",
    help="Specify SQL to select path from input tile layer.")
parser.add_argument(
    "-targs",
    dest="TARGS",
    help='''Specify target argument list (as a quoted string).
            Will override parameter file definition.''')
parser.add_argument(
    "-use_local",
    dest="USE_LOCAL",
    choices=[0, 1], #store_true does not work if we want to override a file definition...
    type=int,
    help="Force using a local spatialite database for reporting (value must be 0 or 1).")
parser.add_argument(
    "-mp",
    dest="MP",
    type=int,
    help="Specify maximal number of processes to spawn (defaults to number of kernels).")
parser.add_argument(
    "-statusinterval",
    dest="STATUS_INTERVAL",
    help='''Specify an interval for which to run status updates
            (if method is defined in parameter file - default 1 hour).''')
group = parser.add_mutually_exclusive_group()
group.add_argument(
    "-refcon",
    dest="REF_DATA_CONNECTION",
    help="Specify connection string to (non-tiled) reference data.")
group.add_argument(
    "-reftiles",
    dest="REF_TILE_DB",
    help="Specify path to reference tile db")

#SQL to create a local sqlite db - should be readable by ogr...
CREATE_SQLITE_DB = """CREATE TABLE __tablename__(
                        id INTEGER PRIMARY KEY,
                        tile_name TEXT,
                        las_path TEXT,
                        ref_path TEXT,
                        prc_id INTEGER,
                        exe_start TEXT,
                        exe_end TEXT,
                        status INTEGER,
                        rcode INTEGER,
                        msg TEXT)"""

INIT_DB = """SELECT InitSpatialMetadata(1)"""

ADD_GEOMETRY = """SELECT AddGeometryColumn('{tablename}',
                                           'geom',
                                           {epsg},
                                           'POLYGON',
                                           'XY')"""


def create_process_db_sqlite(testname, matched_files):
    '''
    Setup process db for organizing parallel processing.
    '''


    db_name = testname + "_{0:d}".format(int(time.time())) + ".sqlite"

    try:
        con = spatialite.connect(db_name)
        cur = con.cursor()
    except spatialite.Error, msg:
        raise ValueError("Invalid sqlite db.")

    cur.execute(INIT_DB)
    cur.execute(CREATE_SQLITE_DB.replace("__tablename__", testname))
    cur.execute(ADD_GEOMETRY.format(tablename=testname, epsg=constants.EPSG_CODE))
    con.commit()

    pid = 0
    for lasname, vname in matched_files:
        tile = constants.get_tilename(lasname)
        wkt = constants.tilename_to_extent(tile, return_wkt=True)
        geom = "GeomFromText('{0}', {1})".format(wkt, constants.EPSG_CODE)
        sql = '''INSERT INTO {test}
                         (id, tile_name, las_path, ref_path, status, geom)
                       VALUES
                         ({pid}, '{tile_name}', '{las_path}', '{ref_path}', {status}, {geom})
                    '''.format(
                            test=testname,
                            pid=pid,
                            tile_name=tile,
                            las_path=lasname,
                            ref_path=vname,
                            status=0,
                            geom=geom
                        )
        cur.execute(sql)
        con.commit()

        pid += 1

    con.commit()
    cur.close()
    con.close()
    return db_name


def main(args):
    '''
    Main processing loop.
    '''
    pargs = parser.parse_args(args[1:])
    if pargs.testhelp is not None:
        #just print some help...
        if not pargs.testhelp in qc.tests:
            print(pargs.testhelp + " not mapped to any test.")
            show_tests()
        else:
            test_usage = qc.usage(pargs.testhelp)
            if test_usage:
                test_usage()
            else:
                print("No usage defined in " + pargs.testhelp)
        return 1
    #Start argument handling with commandline taking precedence...
    return_code, matched_files, args = setup_job(QC_WRAP_NAMES,
                                                 QC_WRAP_DEFAULTS,
                                                 pargs.__dict__,
                                                 pargs.param_file)
    if return_code != 0:
        #something went wrong - msg. should have been displayed
        return return_code

    print("Running qc_wrap at %s" % (time.asctime()))
    if not os.path.exists(LOGDIR):
        print("Creating " + LOGDIR)
        os.mkdir(LOGDIR)

    ############################
    ## Start processing loop   #
    ############################

    testname = args["TESTNAME"]
    use_ref_data = qc.tests[args["TESTNAME"]][0]
    if len(matched_files) > 0:
        #Create db for process control...
        lock = multiprocessing.Lock()
        db_name = create_process_db_sqlite(testname, matched_files)
        if db_name is None:
            print("Something wrong - process control db not created.")
            return 1
        if args["MP"]:
            n_workers = args["MP"]
        else:
            n_workers = multiprocessing.cpu_count()
        assert n_workers > 0

        n_tasks = min(n_workers, len(matched_files))
        print("Starting %d process(es)." % n_tasks)
        if args["RUN_ID"] is not None:
            print("Run-id is set to: %d" % args["RUN_ID"])
        print("Using process db: " + db_name)

        tasks = []
        for i in range(n_tasks):
            test_args = (i, testname, db_name, args["TARGS"], args["RUN_ID"],
                         args["USE_LOCAL"], args["SCHEMA"], use_ref_data, lock)
            worker = multiprocessing.Process(
                target=run_check,
                args=test_args)
            tasks.append(worker)
            worker.start()

        #Now watch the processing#
        con = spatialite.connect(db_name)
        cur = con.cursor()
        n_todo = len(matched_files)
        n_crashes = 0
        n_done = 0
        n_err = 0
        n_left = n_todo
        n_alive = n_tasks
        #start clock#
        time1 = time.time()  #we don't wanne measure cpu-time here...
        t_last_report = 0
        t_last_status = time1

        while n_alive > 0 and n_left > 0:
            time.sleep(5)

            try:
                cur.execute("""SELECT COUNT()
                               FROM {test}
                               WHERE status>?""".format(test=testname), (STATUS_PROCESSING,))
            except spatialite.OperationalError, err_msg:
                print('Database Error: {msg}. Trying again.'.format(msg=err_msg))
                continue

            n_done = cur.fetchone()[0]
            n_alive = 0
            for task in tasks:
                n_alive += task.is_alive()

            #n_left: those tiles which have status 0 or STATUS_PROCESSING
            n_left = n_todo - n_done
            f_done = (float(n_done) / n_todo) * 100
            now = time.time()
            delta_t = now - time1
            dt_last_report = now - t_last_report
            dt_last_status = now - t_last_status
            if dt_last_report > 15:
                if n_done > 0:
                    delta = timedelta(seconds=n_left * (delta_t / n_done))
                    t_left = delta - timedelta(microseconds=delta.microseconds)
                else:
                    t_left = "unknown"

                status_msg = "[qc_wrap - {0}]: Done: {1:.1f} pct, tiles left: {2:d}, "\
                             "estimated time left: {3:s}, active: {4:d}"
                print(status_msg.format(testname, f_done, n_left, t_left, n_alive))

                cur.execute("""SELECT COUNT()
                               FROM {test}
                               WHERE status=?""".format(test=testname), (STATUS_ERROR,))

                n_err = cur.fetchone()[0]
                if n_err > 0:
                    print("[qc_wrap]: {0:d} exceptions caught. Check sqlite-db.".format(n_err))
                t_last_report = now
                if args["status_update"] and dt_last_status > args["STATUS_INTERVAL"]:
                    args["status_update"].update(args["TESTNAME"], n_done, n_err, n_alive)
                    t_last_status = now
            #Try to keep n_tasks alive... If n_left>n_alive,
            # which means that there could be some with status 0 still left...
            if n_alive < n_tasks and n_left > n_alive:
                print("[qc_wrap]: A process seems to have stopped...")
                n_crashes += 1
        time2 = time.time()
        print("Running time %s" % (timedelta(seconds=time2 - time1)))
        cur.execute("SELECT COUNT() FROM " + testname + " WHERE status>?", (STATUS_PROCESSING,))
        n_done = cur.fetchone()[0]
        cur.execute("SELECT COUNT() FROM " + testname + " WHERE status=?", (STATUS_ERROR,))
        n_err = cur.fetchone()[0]
        print("[qc_wrap]: Did {0:d} tile(s).".format(n_done))
        if n_err > 0:
            print("[qc_wrap]: {0:d} exceptions caught - check logfile(s)!".format(n_err))
        cur.close()
        con.close()

    print("qc_wrap finished at %s" % (time.asctime()))
    if args["post_execute"] is not None:
        args["post_execute"].update(args["TESTNAME"], n_done, n_err, n_alive)

    return n_err + n_crashes


if __name__ == "__main__":
    main(sys.argv)

