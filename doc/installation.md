# A more or less complete guide to setting up the DHMQC system #

Throughout this guide we will assume that you are using windows. If not, you'll probably be clever enough to translate to your own OS.

## Downloading dependencies ##

1. Download and install [git](https://git-scm.com/downloads) (default settings are fine)
2. Open a cmd shell, `cd` to a directory where you want to have you repository.
3. Type `git clone https://github.com/Kortforsyningen/DHMQC.git`

Now you should have the repository located in a folder named DHMQC.

Then
 
1. Download [Osgeo4w](http://trac.osgeo.org/osgeo4w/) - choose the 64-bit installer
2. Run the installer and choose 'Advanced install', 'Install from internet' and  'Install for all users'. Choose default selections until you come to 'Select packages'.
3. Make sure the packages `gdal`, `gdal-dev-python`, `python-numpy`, `python-scipy` and `python-pandas` are selected, and proceed with the install. 

If you haven't got a working compiler installed (Visual Studio, mingw, etc.), you can install a compiler from [here](http://mingw-w64.sourceforge.net/download.php) (MingW-W64-builds is fine). Make sure you choose the right target architecture in the installer (e.g. x86_64).

When installing MingW-W64, use settings architecture x86-64, threads win32.

In order to run the build script, you must have python and your compiler set up in the same environment. You can do that in the Osgeo4W64 environment by adding batch scripts to the folder: <osgeo4w_root>\etc\ini. 

Make sure to NOT include "" around your path, when you set the path to e.g. git, i.e.:
```dos
set PATH=%PATH%;C:\Program Files\git
```

and NOT:

```dos
set PATH=%PATH%;"C:\Program Files\git"
```

Install python packages `patch` and `laspy`:
```dos
pip install patch
pip install laspy
```

To build binaries:
```dos
python src\build\build.py -x64 (and possibly -msvc and -PG "<cstr>", see below")
```

Test that your installation by running the following command from the root of the repository:

```dos
nosetests
```


### Set up a Postgis database ###


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
