#Use tile_coverage.py to set up input and reference tile_layers 
TESTNAME="count_classes" #must be one of the valid test-names defined in qc.__init__
#This name must be defined
INPUT_TILE_CONNECTION="some ogr-readable layer containing tilenames"
#This can be defined and not None - will otherwise assume an attributte named 'path' exists in first layer of datasource
INPUT_LAYER_SQL="OGR - sql to select path attributte of tiles" #e.g. select path from coverage, or select some_field as path from some_layer where some_attr=some_value
#DB-setup for reporting of test results
USE_LOCAL=True  #Use local db for reporting (instead of PostGIS-layer) 
SCHEMA=None #"Some Postgres schema e.g. blockxx_2015" only relevant if USE_LOCAL is False
#if test is using reference data - one of these names must be defined, listed in order of precedence
REF_DATA_CONNECTION="a db connection or path to a seamless vector datasource - for vector data which is not tiled"
REF_TILE_DB="path to an ogr readable tile layer" #if REF_DATA_CONNECTION is not defined, this must point to a tile-db similar to one created by, by tile_coverage.py
#PROCESS SPECIFIC CONTROLS
MP=4  #maximal number of processes to spawn - will use qc_wrap default if not defined.
RUN_ID=None #can be set to a number and passed on to reporting database.
#ADDITIONAL ARGUMENTS TO PASS ON TO TEST:
TARGS=["-some_argument","and_its_value","-some_other_arg","its_value","-foo","-bar","-layersql","select wkb_geometry from mylayer where ST_Area(wkb_geometry)>0.1"] #or TARGS=[]



