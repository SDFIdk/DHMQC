# DHMQC Details

DHMQC is the Digital Height Model Quality Control system (DHMQC) used by the Danish Agency for Supply and Effeciency (Styrelsen for Dataforsyning og Effektivisering). For general information about the Agency, contact information etc. please refer to [sdfe.dk](http://sdfe.dk/).

## What is this?

DHMQC is a set of scripts written in python for quality control of large area airborne LiDAR point clouds.
These scripts are backed by library functionality written in Python and C.

## Guide to setup and usage ##

See below. A more or less complete guide on how to setup the system and run tests can be found [here](installation.md).

## Reference data

A lot of tests require reference vector data like roads, houses, lakes etc. Relevant data for Denmark can be downloaded from [kortforsyningen](http://download.kortforsyningen.dk/).

As of February 2015 the easiest way to do this is:

* Create new user: "Opret ny bruger" on the pane to the right. Video instructions [here](https://www.youtube.com/watch?v=2e2T_NR5-uw)
* Go to ["Grundlæggende landkortdata"](http://download.kortforsyningen.dk/content/geodanmark).
* Choose "Hele landet" (entire country) and press "næste" (next)
* Accept "shape" and "UTM32ETRS89" and press "næste" (next)
* Press "Læg i kurv" (add to basket)
* Press "Gennemfør bestillingen" (proceed to check-out). You may be prompted for username/password.
* Follow the link to "Du kan downloade dine ordrer her" (You can download your data here)
* Download the zip file

## Branches

The master branch is (**currently**) changing a lot, so expect that you'll have to adopt various changes and rebuild frequently if you want to use the bleeding edge branch. The stable branch **should** be more stable with features and optimizations being ported from the default branch only when they seem important enough.

So a user who wants to use the default branch should typically:

* Run "git pull" to get updates
* Run a rebuild (if there are C-source changes): `python src\build\build.py <args>`
* Perhaps check that everything works with `python test_suite.py`


##Tiling scheme

The system uses a global tiling scheme which is defined in dhmqc_constants.py, and can be redefined there. It is assumed that the extent of an input (las,laz) pointcloud is encoded in the filename. For 1km tiles (the current tile size) an input file should contain the tokens:

1km_nnnn_eee , where nnnn and eee are is the northing and easting coordinates of the lower left corner in whole kilometers in the reference system UTM32-ETRS89.

E.g. a filename like test123_1km_6169_451_2014.las would fullfill this requirement.

##las or laz

Laspy can read las-files. laz-files can also be read if laszip-cli can be located (in your PATH, current directory etc).

##Invoking tests
Most tests in the qc folder can be called "stand alone", `python some_test.py <args>`, or from the wrapper `qc_wrap.py`. Use `some_test.py -h`, to invoke a usage message.

Typically a test is invoked on a single tile (from the qc-folder):

```
python some_test.py path/to/las/tile.las /path/to/reference/tile.something <optional args>
```

Among the optional args `-use_local` (if reporting to a db) will usually specify that we want to use a local spatialite db rather than a global POSTGIS db. When invoking tests like this the schema and runid parameters are *not* supported (yet).

### Wrapping tests with qc_wrap.py ###

qc_wrap is designed to set up long running tasks for a lot of tiles using multiprocessing. Various options are set up in a parameter file (see args_template.py). E.g. if a test is using reference data, like e.g. road or building features, the connection to a datasource must be defined in the parameter file (which can then be reused).

qc_wrap uses a sqlite database for process synchronization and it is possible to keep track of progess by loading this into e.g. QGIS.

Tile layers for input tiles and reference tiles can be created with the tile_coverage.py utility. For example if you have a bunch of las files (with names defined according to the tiling scheme) in C:\lasdir and a bunch of shape-files in C:\refdir, you can:

1. run: `python tile_coverage.py create C:\lasdir las las_tiles.sqlite`
2. run: `python tile_coverage.py create C:\refdir shp roads_tiles.sqlite`
3. Define TESTNAME="z_precision_roads", INPUT_TILE_CONNECTION="las_tiles.sqlite",INPUT_LAYER_SQL="select path from coverage" (not needed - but handy) , REF_TILE_DB="road_tiles.sqlite" in your parameter script (e.g. params.py)
4. run: `python qc_wrap.py params.py` - this will create a new sqlite-db called `z_precision_roads_<some_number>.sqlite` which you can load into e.g. QGIS to keep track of progess.

If instead you have road features in a POTSGIS database (or just some OGR-readable seamless datasource) you can skip step 2, and in step 3 instead define:

* REF_DATA_CONNECTION="PG: some-connection string to your database"
* The test should support a "-layersql" argument for selecting features from a table, so you could e.g. specify: TARGS=["-layersql","select wkb_geometry from <my_table> where <some_attr>=<some_value>"]

The SQL-statement is very flexible, and allows you to also modify geometries using POSTGIS-functions. e.g.:


```sql
select ST_Buffer(wkb_geometry,5.0) from myroadlayer where ST_Intersects(wkb_geometry,ST_GeomFromText(WKT_EXT,25832))
```

The token WKT_EXT acts as a placeholder (defined in thatsDEM/vector_io.py) which will be expanded to the actual area of interest. Specifying the "area of interest" directly  seems to result in much faster queries compared to setting a generic OGR spatial filter on the layer (which will happen by default).

If the datasource is just e.g. a plain shapefile, modify the SQL-statement, or leave it undefined in which case all features (which intersects the tile)  from first layer are selected.

The INPUT_TILE_CONNECTION must be an OGR readable datasource. This can created by tile_coverage.py, but could also be a global database connection or simply a shapefile or a geojson file. The INPUT_LAYER_SQL allows a high flexibility to select subsets of tiles, e.g. "select path from <some_table> where <time_stamp_field> > <some_number>"...

Some arguments can be defined either in the parameter file or on the command-line - if both are defined the command line will take precedence. This allows for easier batching a lot of tests without having to edit a lot of parameter files.
(It could be implemented that these options can be read from environment variables also.)

So e.g. in a batch / shell script one can write:

```dos
set RUNID=999
set TILES=C:\Dev\some_tiles.sqlite
set SCHEMA="test"
python qc_wrap.py args_road_check.py -tiles %TILES% -runid %RUNID% -schema %SCHEMA%
python qc_wrap.py args_density_check.py -tiles %TILES% -runid %RUNID% -schema %SCHEMA%
```

or - e.g. if you haven't created a tile-layer yet

```dos
set RUNID=999
set TILES=C:\Dev\some_tiles.sqlite
set SCHEMA="test"
python tile_coverage.py create <path_to_las_files> las %TILES%
python qc_wrap.py args_road_check.py -tiles %TILES% -runid %RUNID% -schema %SCHEMA%
python qc_wrap.py args_density_check.py -tiles %TILES% -runid %RUNID% -schema %SCHEMA%

```
In order to easier support quick and dirty batching of tests, it is now not necessary to specify a parameter file. Most "keys" can be specified on the commandline (eventually all). Keywords can be defined either in a parameter file or on the command line, with the command line taking precedence.  So one can e.g. do:


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

##Reporting to a database##

Most tests aggregate results in a database via the reporting module (qc/db/report.py), while a few will just produce e.g. grid outputs. The system is set up so that you can report either to a PostGis  database (default) or to a local Spatialite db.

**UPDATE** : db functionality has been moved to a submodule qc/db

### Reporting to a PostGis database ###

* When you build with build.py, use the -PG option, e.g. build.py -x64 -msvc -PG "host='somehost' dbname='something' user='someuser' password='passwd'"
* Or, simply manually create a file named pg_connection.py in qc/thatsDEM containing a single line: PG_CONNECTION="PG: <connection string as above>"

You only need to do this once. You can set up a schema in the PostGis db by:

```
python db_create_schema.py <some_schema>
```

and copy styling from another schema by:

```
python db_retrieve_styling.py <schema_with_styling> <schema_without_styling>
```

A few useful views can be created by:

```
python db_create_views.py <schema>
```

Then when invoking a test from qc_wrap.py, specify USE_LOCAL=False and SCHEMA=<some_schema>. If the schema is not defined qc_wrap will create it automatically.

When invoking a test ** directly** ("stand alone"), just leave out the option -use_local. The test will then try to report to a default schema named "dhmqc" (and will fail if that schema is not created).

### Reporting to a local Spatialite database ###

If a test is invoked "stand alone" (i.e. not from qc_wrap) and with the command line argument -use_local it will report to a local Spatialite db named dhmqc.sqlite in the current folder (which must exist). If invoked from qc_wrap.py and USE_LOCAL=True, tests will also report to a local Spatialite db named dhmqc.sqlite in the current folder, but will also create a new db if it doesn't exist.

A new db can always be created with the script recreate_local_datasource.py in the qc-folder.

So e.g. if you are testing out something, before starting a huge job with qc_wrap:



```dos
python recreate_local_datasource.py
python z_precision_roads.py 1km_6169_451.las roads.geojson -use_local
python z_accuracy_gcp.py 1km_6169_451.las gcps.shp -use_local
python density_check.py 1km_6169_451.las "PG: host='localhost' dbname='maps' user='me' password='abc'"
-lakesql "select wkb_geometry from water.sea_plus_lakes where st_intersects(wkb_geometry,st_geomfromtext(WKT_EXT,25832))"  -use_local -outdir C:\data\density
python density_check.py 1km_6169_451.las some_polygons_containing_water.shp -use_local -cs 2.0

```

### Optimizing performance ###
Depending on IO performance of the disk where las or laz files are stored some tests will be either CPU bound or IO bound. If performance is limited by IO it is not benefitial to run many processes. The balance depends on the test and whether LIDAR data is stored as las or laz (less prone to be IO-bound).
