# A more or less complete guide to setting up the DHMQC system #

## Getting DHMQC up and running ##
### Prerequisites ###
Ensure you have the following installed:
* Git (for cloning the repo)
* Your preferred Conda/Mamba distribution ([Miniforge](https://github.com/conda-forge/miniforge) is recommended)
* C and C++ compilers (on Unix, `gcc` and `g++`). For Windows, install [MinGW-w64](https://www.mingw-w64.org/downloads/)

### Clone the DHMQC repository ###
Clone the repository using Git. You should now have a copy of repository located in a folder named `DHMQC`. `cd` into this directory, the rest of the installation procedure will take place from here.

### Setting up a Conda environment ###
* Create a new environment with `conda env create -f environment.yml -n DHMQC_ENV` (replace `DHMQC_ENV` with your desired name for the environment).
* Switch to your new environment with `conda activate DHMQC_ENV` (replace `DHMQC_ENV` with the name entered above). To be able to use DHMQC, you need to be in this environment.

### Building binaries ###
Some parts of DHMQC are implemented in C/C++ and must be built before use. From the root of your `DHMQC` directory, enter
```dos
python src/build/build.py -x64 -force -cc PATH/TO/GCC -cxx PATH/TO/G++
```
Substitute `PATH/TO/GCC` and `PATH/TO/G++` with `gcc` and `g++` if available, otherwise with paths to the respective MinGW .exe files. Typical paths for MinGW-w64 are `"C:\Program Files\mingw-w64\<VERSION>\mingw64\bin\gcc.exe"` and `"C:\Program Files\mingw-w64\<VERSION>\mingw64\bin\g++.exe"`.

### Running unit tests ###
Test that your installation works by running the following command from the root of the repository:

```dos
nosetests
```

## Set up a Postgis database ##


If you want to use reporting of qc-results to a Postgis db, you should install [Postgis](http://postgis.net/install/) and create a database. You will need to tell dhmqc what the connection string to your database is - this can be done in the setup script with the -PG "<connection_string> option or by simply placing a file named `pg_connection.py` in the `qc/db` folder, which defines 


```python
PG_CONNECTION="<connection_string>"
```

A template is provided in `qc/db/pg_connection.py.template`.

Then create a schema with:


```dos
python db_create_schema.py <some_schema>
```
If you do not create a schema, qc_wrap will do that for you when you specify output to some schema in your parameter file or from the commandline: -schema <some_schema>.

If you have set up a schema with a lot of nice styling, and want to copy that to another schema you can use:


```dos
python db_retrieve_styling.py <schema_with_styling> <schema_without_styling>
```

You do not have to setup a Postgis db, it's possible to stick with a local Spatialite db instead. Just use the -use_local argument when invoking a test, or specify USE_LOCAL=True, when invoking a test from qc_wrap.py.

## A complete example on how to run a test from qc_wrap ##

Say you have a bunch a las/laz files using the right tiling scheme (<prefix>_1km_NNNN_EEE_<postfix>.las) in the folder C:\data\las, and a spatialite database containing road-lines downloaded from [kortforsyningen](http://download.kortforsyningen.dk) in C:\data\refdata.sqlite. You can now:

Create an index of your las-tiles with: 

```dos
python tile_coverage.py create C:\data\las las C:\data\lasindex.sqlite.
```
You do not need to use tile_coverage.py, as long as you have some kind of vector layer with a field which contains the path to las files, you can use the INPUT_LAYER_SQL token to select the path field.

Specify an argument script for qc_wrap as:


```python
TESTNAME="z_precision_roads" 
#This name must be defined
INPUT_TILE_CONNECTION="C:/data/lasindex.sqlite"
#INPUT_LAYER_SQL="" only define this if you do not want to check all tiles.
USE_LOCAL=True #Use local db for reporting (instead of PostGIS-layer) 
REF_DATA_CONNECTION="C:/data/refdata.sqlite"
#PROCESS SPECIFIC CONTROLS
MP=4  #maximal number of processes to spawn - will use number of kernels if not specified.
#ADDITIONAL ARGUMENTS TO PASS ON TO TEST:
TARGS=["-layersql","select GEOMETRY from roads where st_intersects(GEOMETRY,st_geomfromtext(WKT_EXT,25832))"] 
```
The  "where st_intersects(GEOMETRY,st_geomfromtext(WKT_EXT,25832))" will speed things up slightly, but is not needed. Save that file as e.g., templates\params_roads.py , and run:


```dos
python qc_wrap.py templates\params_roads.py
```

If instead you have tiled your reference road data into a lot of shape-files, using the same tiling scheme as for the las files, run:


```dos
python tile_coverage.py create <path_to_tile_root> shp C:\data\roadtiles.sqlite
```
to create a tile index for your reference road data.

Say, that you also have set up a Postgis db and want to report into a schema named "test". Then instead use the following argument file:

```python
TESTNAME="z_precision_roads" 
#This name must be defined
INPUT_TILE_CONNECTION="C:/data/lasindex.sqlite"
#INPUT_LAYER_SQL="" only define this if you do not want to check all tiles or your tile layer is not created with tile_coverage.py
USE_LOCAL=False
SCHEMA="test"
RUN_ID=1  # you can also set this for a local spatialite db
REF_TILE_DB="C:/data/roadtiles.sqlite"
#PROCESS SPECIFIC CONTROLS
MP=4  #maximal number of processes to spawn - will use number of kernels if not specified.
#ADDITIONAL ARGUMENTS TO PASS ON TO TEST:
#TARGS=[]

```

In order to easier support quick and dirty batching of tests, it is *now* not necessary to specify a parameter file. Most "keys" can be specified on the commandline (eventually all). Keywords can be defined either in a parameter file or on the command line, with the command line taking precedence.  So one can e.g. do:


```dos
REM start of classification batch tests (not producing grids)
set RUNID=1
set TILE_DB=E:\B01\las_coverage.sqlite
set SCHEMA=class_b01
set REFCON="PG: host='localhost' dbname='maps' user='postgres' password='postgres'"
set HOUSES='select wkb_geometry from geodk.bygning where ST_Intersects(wkb_geometry,ST_GeomFromText(WKT_EXT,25832))'
set LAKES='select wkb_geometry from geodk.soe where ST_Intersects(wkb_geometry,ST_GeomFromText(WKT_EXT,25832))'
REM python qc_wrap.py -testname spike_check -schema %SCHEMA% -targs "-zlim 0.25" -tiles %TILE_DB% -runid %RUNID%
REM python qc_wrap.py -testname count_classes -schema %SCHEMA% -tiles %TILE_DB% -runid %RUNID%
python qc_wrap.py -testname classification_check -schema %SCHEMA% -tiles %TILE_DB% -runid %RUNID% -refcon %REFCON% -targs "-type building -layersql %HOUSES%"
python qc_wrap.py -testname classification_check -schema %SCHEMA% -tiles %TILE_DB% -runid %RUNID% -refcon %REFCON% -targs "-type lake -layersql %LAKES%"

```
