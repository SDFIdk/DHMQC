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
##########################################
## Base functionality for processing definitions (meta meta)  #
##########################################
import os,sys, time
from osgeo import ogr
import qc
from qc.thatsDEM import remote_files
from qc.db import report
from qc import dhmqc_constants as constants
import shlex

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
QC_WRAP_NAMES={"TESTNAME":str,
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

#Names which are relevant for job definitions for the 'listening client'
PCM_NAMES={"TESTNAME":str,
"SCHEMA":str,
"USE_LOCAL":bool,
"REF_DATA_CONNECTION":unicode,
"REF_TILE_DB":unicode,
"REF_TILE_TABLE":str,
"REF_TILE_NAME_FIELD":str,
"REF_TILE_PATH_FIELD":str,
"RUN_ID":int,
"TARGS":list}

#Placeholders for testname,n_done and n_exceptions
#names that really must be defined
MUST_BE_DEFINED=["TESTNAME","INPUT_TILE_CONNECTION"]
#And for pcm
MUST_BE_DEFINED_PCM=["TESTNAME","TARGS"]
#DEFAULTS FOR STUFF THATS NOT SPECIFIED (other than None):
QC_WRAP_DEFAULTS={"USE_LOCAL":False,"REF_TILE_TABLE":"coverage","REF_TILE_NAME_FIELD":"tile_name","REF_TILE_PATH_FIELD":"path","TARGS":[],"STATUS_INTERVAL":3600}
#DEFAULTS FOR THE LISTENING CLIENT
PCM_DEFAULTS={"USE_LOCAL":False} 

def get_definitions(all_names,defaults,definitions,override=None):
    #all_names is a dict of relevant names and the type we want to convert to...
    #defaults is a dict of default values of correct type which will be used if not given in def1 or def2 
    #definitions is a dict of parsed definitions (json, yaml,  execfile, exec, etc....).
    #override is another similar dict (perhaps from commandline args, which should take precedence and override the first definitions.
    args=dict.fromkeys(all_names.keys(),None) #all is None
    args.update(defaults) #add some defaults if relevant
    #normalise arguments...  iterate over all relevant keys (could be more in definitions or override)
    for key in all_names.keys():
        val=None
        if key in definitions and definitions[key] is not None:
            val=definitions[key]
        if override is not None:
            if key in override and override[key] is not None:
                if val is not None:
                    print("Overriding "+key)
                val=override[key]
        if val is not None:
            #apply converters
            if key=="TARGS":
                if isinstance(val,str) or isinstance(val,unicode):
                    val=shlex.split(val)
            try:
                val=all_names[key](val)
            except Exception,e:
                print("Value of "+key+" could not be converted: \n"+str(e))
                raise e
            if key=="TESTNAME":
                val=os.path.basename(val).replace(".py","")
            args[key]=val
            print("Defining "+key+": "+repr(val))
    return args


def show_tests():
    print("Currently valid tests:")
    for t in qc.tests:
        print("               "+t)




def validate_job_definition(args,must_be_defined,create_layers=True):
    #A refactored job def checker which can be usefull outside of qc_wrap
    #For now simply print both user-info and error messages and return a boolean - this is supposed to be executed from the command line.
    #consider using a logger (info / warning / error).
    for key in must_be_defined:
        if args[key] is None:
            print("ERROR: "+key+ " must be defined.")
            return False
    
    if not args["TESTNAME"] in qc.tests:
        print("%s,defined in parameter file, not matched to any test (yet....)\n" %args["TESTNAME"])
        show_tests()
        return False
    #see if test uses ref-data and reference data is defined..
    use_ref_data=qc.tests[args["TESTNAME"]][0]
    use_reporting=qc.tests[args["TESTNAME"]][1]
    ref_data_defined=False
    for key in ["REF_DATA_CONNECTION","REF_TILE_DB"]:
        ref_data_defined|=(args[key] is not None)
    if use_ref_data:
        if not ref_data_defined:
            print("Sorry, "+args["TESTNAME"]+" uses reference data.\nMust be defined in parameter file in either REF_DATA_CONNECTION or REF_TILE_DB!")
            return False
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
                return False
        else:
            print("No argument parser in "+args["TESTNAME"]+" - unable to check arguments to test.")
        
    if use_reporting:
        if args["USE_LOCAL"]:
            #will do nothing if it already exists
            #should be done 'process safe' so that its available for writing for the child processes...
            if create_layers:
                report.create_local_datasource()
            if args["SCHEMA"] is not None: #mutually exclusive - actually checked by parser...
                print("WARNING: USE_LOCAL is True, local reporting database does not support schema names.")
                print("Will ignore SCHEMA")
        #check the schema arg
        else:
            if args["SCHEMA"] is None:
                print("ERROR: Schema MUST be specified when using a global datasource for reporting!")
                return False
            print("Schema is set to: "+args["SCHEMA"])
            #Test if we can open the global datasource with given schema
            print("Testing connection to reporting db...")
            layers_defined=report.schema_exists(args["SCHEMA"])
            print("Layers defined: "+str(layers_defined))
            if (not layers_defined) and create_layers:
                print("Creating schema/layers...")
                try:
                    report.create_schema(args["SCHEMA"])
                except Exception,e:
                    print("Failed: "+str(e))
                    return False
    return True

def match_tiles_to_ref_data(input_files,args,test_connections=True):
    #Match input files to reference data
    #test wheter we want tiled reference data...
    matched_files=[]
    if args["REF_DATA_CONNECTION"] is not None:
        tiled_ref_data=False
        args["REF_DATA_CONNECTION"]
        print("A non-tiled reference datasource is specified.")
        print("Testing reference data connection....")
        ds=ogr.Open(args["REF_DATA_CONNECTION"])
        if ds is None:
            if test_connections:
                raise Exception("Failed to open reference datasource.")
            else:
                print("Failed to open reference datasource.")
            
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
    return matched_files

def get_input_tiles(input_tile_connection,input_layer_sql=None):
    print("Getting tiles from ogr datasource: "+input_tile_connection)
    input_files=[]
    #improve by adding a layername
    ds=ogr.Open(input_tile_connection)
    if ds is None:
        raise Exception("Failed to open input tile layer!")
        
    if input_layer_sql is not None:
        print("Exceuting SQL to get input paths: "+input_layer_sql)
        layer=ds.ExecuteSQL(str(input_layer_sql))
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
    return input_files