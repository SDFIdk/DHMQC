# HOWTO: Create DTM and DSM from a pointcloud

## Introduction

In this tutorial we demonstrate the capabilities of the DHMQC software package by
creating DTM's and DSM's from a pointcloud and supporting vector-data.

The DHMQC software package has been developed as a part of the nation-wide update of
the Danish Elevation Model, DK-DEM.
For now DHMQC is mostly developed to be used with the DK-DEM dataset, which makes it difficult to use
pointcloud data from a different source.
This is likely to change in the near future since other nation mapping agencies has show an interest in the software package.

## Objective

Turn a pointcloud into digital terrain and surface models and visualize them as hillshades.

## Prerequisites

You need to have a working installation of the [DHMQC package](https://bitbucket.org/GSTudvikler/gstdhmqc/).
Get the most recent version and follow the build instructions in the READE file.
A PostGIS database with write-access is also needed.

For the DTM-generator in DHMQC we need a bunch of input data. These are:

1. Pointcloud (las/laz-files)
2. Lake geometries
3. River geometries
4. Sea geometries
5. Building geometries

The pointcloud data is obviously needed, since we want to generate DTM's from the pointcloud.
Besides the las/laz-files we need supporting vector data.
The supporting data consist of geometries of larger water bodies such as lakes, rivers and the sea.
Furthermore building geometries are needed.

In this guide we use data from the [Danish Agency for Supply and Effeciency](http://sdfe.dk/)
which is freely available at [Kortforsyningen](http://kortforsyningen.dk/).

## Prepare datasources

Before we can get started we need to prepare the datasources.
Preparation of the individual datasources are described below.

### Pointcloud

The pointcloud should be in either las or laz format and have horizontal coordinates in UTM.
Furthermore the pointcloud should be tiled and named according to the Danish Kvadratnet.
This entails that each tile in the pointcloud should be exactly 1 square km.
The naming of tiles describe the geographical extent of the tile.
An example of a correctly named tile is:

> 1km_6175_725.las

Where 1km describes the tile-size.
The numbers are related to the northing and easting (in that order) of the lower left corner of the tile.
To get the coordinates of the lower left corner just multiply the numbers in the tile name by 1000.

The DK-DEM pointcloud is already distributed in the above mentioned naming and tiling scheme.

### Geometries

The following geometries are needed by the DTM/DSM generator.
Since laser-beams from a LIDARs are reflected poorly from water we turn to supporting vector data that outline larger water bodies.

When we create the DTM we need to disregard all points that are not classified as terrain.
Where there are buildings this is usually a problem since we see a lot of points classified
as terrain that in reality lies above the terrain.
Because of this we take advantage of pre-existing building-polygons.
This allows us to disregard terrain points in buildings that presumably are wrongly classified.

The geometries are loaded into a PostGIS database which allows DHMQC to do quick geometry operations on the data.
As mentioned earlier, we use data from The Danish Agency for Supply and Efficiency.
The vector data comes from two different datasets.
The sea polygon is based on the DAGI dataset. DAGI is set of administrative boundaries in Denmark.
We use the municipalities go get a multipolygon that describes the coastline.
The inverse polygon describes the sea around Denmark.
Buildings, lakes and rivers are taken from the GeoDanmark dataset that makes up the basis for danish topographical maps.

#### Sea

The sea is described by a (multi)polygon.
The sea-polygon is used to set a fixed height for the sea-level in the terrain models.

We use the OGR utility ogr2ogr to transfer our sea polygons (sea.shp) into the PostGIS database:

```
>ogr2ogr -t_srs "EPSG:25832" -f "PostgreSQL" PG:"dbname='dhmqc' host='database' user='postgres' password='postgres'" -nln demo.hav dagi\hav.shp
```

#### Lakes

Lake polygons are used in a similar way to the sea polygons.
In a layer step we use the lake polygons and the pointcloud to calculate a heights of the water in lakes.
The calculated heights are then burned into the DTM and DSM.

Loading into PostGIS:

```
> ogr2ogr -t_srs "EPSG:25832" -f "PostgreSQL" PG:"dbname='dhmqc' host='database' user='postgres' password='postgres'" -nln demo.burn_lakes geodk\soe.shp
```

#### Rivers

Rivers, or more correctly, streams are represented by line features.
The line features are used to adjust the models in places where vegetation covers the stream.

Loading into PostGIS:

```
> ogr2ogr -t_srs "EPSG:25832" -f "PostgreSQL" PG:"dbname='dhmqc' host='c1200038' user='postgres' password='postgres'" -nln demo.vandloebsmidte_brudt geodk\vandloebsmidte_brudt.shp
```

#### Buildings

Building polygons are used to correct incorrectly classified points within buildings.

Loading into PostGIS:

```
> ogr2ogr -t_srs "EPSG:25832" -f "PostgreSQL" PG:"dbname='dhmqc' host='c1200038' user='postgres' password='postgres'" -nln demo.bygning geodk\bygning.shp
```

## Intermezzo: Parallel calculations with DHMQC

DHMQC consists of a range of scripts that is used for quality assurance (hence the name), model generation
and pointcloud manipulation.
The scripts are in general meant to be run on a single pointcloud tile.
Most scripts need some sort of input besides the pointcloud, for instance vector data as described above.

The scripts are located in the ```qc``` folder in the DHMQC directory.
They are run as any other python script. Here we see the help text for ```class_grid.py```:

```
C:\dev\gstdhmqc>python qc\class_grid.py --help
usage: class_grid.py [-h] [-cs CS] las_file output_dir

Write a grid with cells representing most frequent class.

positional arguments:
  las_file    Input las tile.
  output_dir  output directory of class grids.

optional arguments:
  -h, --help  show this help message and exit
  -cs CS      Cellsize (defaults to 1.00)
```

Calling the class grid script is as simple as

```
C:\dev\gstdmhqc>python qc\class_grid.py C:\data\las_files\1km_6175_725.las C:\data\class_grids
```

The real power of DHMQC is that because the scripts work on a per tile basis, we can very easily run them in parallel.
Before we can start parallel calculations with DHMQC we need to create a tile index.
The tile index is a sqlite database that contains bounding box geometries and paths to each tile we want to include in our calculations.
The tile index is creating by running the python script ```tile_coverage.py```.
The script is located in the root of the DHMQC folder, for instance ```C:\dev\gstdhmqc```.

For more info on the tile coverage script run

```
C:\dev\gstdhmqc> python tile_coverage.py --help

usage: tile_coverage.py [-h] {create,update,remove} ...

Write/modify a sqlite file readable by e.g. ogr with tile coverage.

positional arguments:
  {create,update,remove}
                        sub-command help
    create              create help
    update              Update timestamp of tiles.
    remove              Remove tiles from one db which exist in another db

optional arguments:
  -h, --help            show this help message and exit
```

You can get a more detailed help text for the sub-commands by running a separate help command.
Here is the help text for the create command:

```
C:\dev\gstdhmqc> python tile_coverage.py create --help
usage: tile_coverage.py create [-h] [--append] [--exclude EXCLUDE]
                               [--include INCLUDE] [--depth DEPTH]
                               [--fpat FPAT] [--overwrite]
                               path ext dbout

create a new database

positional arguments:
  path               Path to directory to walk into
  ext                Extension of relevant files
  dbout              Name of output sqlite file.

optional arguments:
  -h, --help         show this help message and exit
  --append           Append to an already existing database.
  --exclude EXCLUDE  Regular expression of dirnames to exclude.
  --include INCLUDE  Regular expression of dirnames to include.
  --depth DEPTH      Max depth of subdirs to walk into (defaults to full
                     depth)
  --fpat FPAT        Regular expression of filenames to include.
  --overwrite        Overwrite record if tile already exists.
```

Parallel calculations with DHMQC is done with the script ```qc_wrap.py```.
As the name suggest the script is a wrapper for the scripts in the qc-folder.
Using ```qc_wrap.py``` is the recommended way of doing calculations with DHMQC.
Running the qc-scripts directly is only recommended for testing purposes.

The help text for ```qc_wrap.py``` describes how to use the wrapper:

```
C:\dev\gstdhmqc>python qc_wrap.py -h
usage: qc_wrap.py [-h] [-testname TESTNAME] [-testhelp TESTHELP]
                  [-runid RUN_ID] [-schema SCHEMA]
                  [-tiles INPUT_TILE_CONNECTION] [-tilesql INPUT_LAYER_SQL]
                  [-targs TARGS] [-use_local {0,1}] [-mp MP]
                  [-statusinterval STATUS_INTERVAL]
                  [-refcon REF_DATA_CONNECTION | -reftiles REF_TILE_DB]
                  [param_file]

Wrapper rutine for qc modules. Will use a sqlite database to manage multi-
processing.

positional arguments:
  param_file            Input python parameter file.

optional arguments:
  -h, --help            show this help message and exit
  -testname TESTNAME    Specify testname, will override a definition in
                        parameter file.
  -testhelp TESTHELP    Just print help for selected test.
  -runid RUN_ID         Specify runid for reporting. Will override a
                        definition in paramater file.
  -schema SCHEMA        Specify schema to report into (if relevant) for
                        PostGis db. Will override a definition in parameter
                        file.
  -tiles INPUT_TILE_CONNECTION
                        Specify OGR-connection to tile layer (e.g.
                        mytiles.sqlite). Will override INPUT_TILE_CONNECTION
                        in parameter file.
  -tilesql INPUT_LAYER_SQL
                        Specify SQL to select path from input tile layer.
  -targs TARGS          Specify target argument list (as a quoted string) -
                        will override parameter file definition.
  -use_local {0,1}      Force using a local spatialite database for reporting
                        (value must be 0 or 1).
  -mp MP                Specify maximal number of processes to spawn (defaults
                        to number of kernels).
  -statusinterval STATUS_INTERVAL
                        Specify an interval for which to run status updates
                        (if method is defined in parameter file - default 1
                        hour).
  -refcon REF_DATA_CONNECTION
                        Specify connection string to (non-tiled) reference
                        data.
  -reftiles REF_TILE_DB
                        Specify path to reference tile db

```

As you can see, there's a few different ways you can use the wrapper script.
Either you specify all parameters on the command line or you define them in a
script that is then used as an input for ```qc_wrap.py```.

In the command line only method you specify which test you want to run with the
```-testname``` argument.
After that you tell the wrapper where your tile index is located by using the
argument ```-tiles```.
Lastly you need to specify the call-arguments of the test you are running.
That is done with the ```-targs``` argument.
Here's an example of running the class grid script in parallel:

```
C:\dev\gstdhmqc>python qc_wrap.py -testname class_grid -tiles coverage.sqlite -targs "C:/data/class_grids"
```

The ```-targs```argument is simple in this case: We only need to state the output directory of the script!

Alternatively we could set up a parameter file instead of writing all the arguments on the command line.
Some of the scripts take a lot of complicated input arguments and writing them in a parameter file makes
the setup a lot easier.
If we want to run the same calculations as above but by using a parameter file, we get something like this:

```
OUTDIR = 'C:/data/class_grids'
TILE_DB = 'coverage.sqlite'
MP = 2
TESTNAME = 'class_grid'

TARGS = [TILE_DB, OUTDIR]
```

Here we have the setup the same wrapper as above with an additional argument: MP.
The MP argument defines how many simultaneous processes the script is running.

Calling ```qc_wrap.py``` with the parameter file is simple:

```
C:\dev\gstdhmqc> python qc_wrap.py params.py
```

## Back on track

Now that we have the datasources in place and we have a basic understanding of how DHMQC works,
we can start the real calculations.
In order to create a DTM and a DSM and then visualize them as hillshades we need to go through a few steps.
As stated earlier we use the vector data as supporting data when creating the two models.
Most of the vector data is used directly, but before we can start calculating DTM and DSM
we need to prepare the lake geometries.
Lake geometries are used to set homogeneous heights across the lake.
In order to use a set height for lakes we need to calculate the height first.
In principle you could do this on the fly while generating the DTM and DSM,
but when you have large lakes that span more than one tile that strategy becomes unviable.
For that reason we go through each lake geometry and determine it's ideal height across several tiles.

After the lakes heights have been set, we can start creating the DTM and DSM.
We do that by making a parameter file for ```qc_wrap.py``` that sets up all the input datasources etc.

When the DTM and DSM are ready we create hillshades based on the newly created models.

### Calculate lake heights

When calculating the lake heights we use the script ```set_lake_z.py```.
The lake heights are determined by looking at all points within the lake.
The height is determined as the 12.5 percentile of all heights within the lake.
Except when the heights differ too much, then no height is recorded and the
lake is triangulated the same way as the terrain.
We do this because we don't want lake heights that are higher than the surrounding terrain.

Before we can start the lake height calculations we need to do a bit of setup.
First of all, we need a tile index in order to use ```qc_wrap.py```:

```
C:\dev\gstdhmqc> python tile_coverage.py create C:\Temp\pc2dtm\PC_617_72 laz C:\Temp\pc2dtm\coverage.sqlite

Creating coverage table.
C:\Temp\pc2dtm\data\PC_617_72
Inserted/updated 97 rows
Encountered 0 'dublet' tilenames
Encountered 0 bad tile-names.
```

We already loaded the vector data in to the database.
Now we need to add a few columns to the table that stores the lake geometries.
We do that by calling the script ```set_lake_z.py```directly and specify ```__db__``` as the input tile.
The script knows that when ```__db__``` is entered it is in setup mode.
We use te ```-db_action``` argument to state what we want the script to do.
Here we use "setup" to add columns to the lake table:

```
C:\dev\gstdhmqc> python qc\set_lake_z.py __db__ "dbname='dhmqc' host='c1200038' user='postgres' password='postgres'" demo.burn_lakes -db_action setup
```

We also need to populate the new columns with some data:

```
C:\dev\gstdhmqc> python qc\set_lake_z.py __db__ "dbname='dhmqc' host='database' user='postgres' password='postgres'" demo.burn_lakes -db_action reset
```

After the lake tables have been created and set up we can start the calculations:

```
C:\dev\gstdhmqc> python qc_wrap.py -testname set_lake_z -tiles C:\Temp\pc2dtm\coverage.sqlite -targs "-nowarp 'dbname=dhmqc host=database user=postgres password=postgres' demo.burn_lakes"
```

The arguments in ```-targs```are ```-nowarp```, the database connection string and
the output table where the results are stored.

The output from ```set_lake_z.py``` is:

```
Defining INPUT_TILE_CONNECTION: u'C:\\Temp\\pc2dtm\\coverage.sqlite'
Defining TESTNAME: 'set_lake_z'
Defining TARGS: ['-nowarp', 'dbname=dhmqc host=database user=postgres password=postgres', 'demo.burn_lakes']
Validating arguments for set_lake_z
Getting tiles from ogr datasource: C:\Temp\pc2dtm\coverage.sqlite
No SQL defined. Assuming we want the first layer and attribute is called 'path'
Found 97 tiles.
Running qc_wrap at Tue Feb 23 20:29:20 2016
Starting 4 process(es).
Using process db: set_lake_z_1456255760.sqlite
[qc_wrap - set_lake_z]: Done: 1.0 pct, tiles left: 96, estimated time left: 480.10 s, active: 4
[qc_wrap - set_lake_z]: Done: 2.1 pct, tiles left: 95, estimated time left: 955.46 s, active: 4
[qc_wrap - set_lake_z]: Done: 10.3 pct, tiles left: 87, estimated time left: 306.51 s, active: 4
...
[qc_wrap - set_lake_z]: Done: 99.0 pct, tiles left: 1, estimated time left: 5.07 s, active: 1
[qc_wrap - set_lake_z]: Done: 99.0 pct, tiles left: 1, estimated time left: 5.22 s, active: 1
[qc_wrap - set_lake_z]: Done: 99.0 pct, tiles left: 1, estimated time left: 5.38 s, active: 1
Running time 521.54 s
[qc_wrap]: Did 97 tile(s).
qc_wrap finished at Tue Feb 23 20:38:02 2016
```

We now have a set of lakes that have a height attached. Those can now be used when creating the terrain models.

### Running the DTM and DSM script

Creation of DTM and DSM are done with the script ```dem_gen_new.py```.
The setup of DEM generator is fairly complicated, so we do that with a paramter file.
Below the parameter file ```params.py``` is seen.

```python
#params.py
import json

OUTDIR = 'C:\Temp\pc2dtm\dems\dtmdsm'
TILE_DB = 'C:\Temp\pc2dtm\coverage.sqlite'

INPUT_TILE_CONNECTION = TILE_DB
CON = "PG: host='database' dbname='dhmqc' user='postgres' password='postgres'"
BBOX = "where ST_Intersects(wkb_geometry,ST_GeomFromText(WKT_EXT,25832))"  # WKT_EXT is replaced when called from qc_wrap.py

LAYERS = {
"RIVER_LAYER": (CON, "select ST_Buffer(wkb_geometry,3) from demo.vandloebsmidte_brudt " + BBOX + " and synlig='1' and midtbredde!='0-2.5'"),
"BUILD_LAYER": (CON, "select wkb_geometry from demo.bygning " + BBOX),
"LAKE_LAYER": (CON, "select wkb_geometry from demo.burn_lakes " + BBOX),
"LAKE_Z_LAYER": (CON, "select wkb_geometry,burn_z from demo.burn_lakes " + BBOX + " and is_invalid=0 and burn_z is not null and has_voids=1"),
"SEA_LAYER": (CON, "select wkb_geometry from demo.hav " + BBOX),
"LAKE_Z_ATTR":"burn_z"
}

MP = 4
TESTNAME = 'dem_gen_new'

TARGS = [TILE_DB, OUTDIR,
        '-dtm',
        '-dsm',
        '-overwrite',
        '-hsys', 'dvr90',
        '-nowarp',
        '-triangle_limit', '2.5',
        '-clean_buildings',
        '-zlim', '0.4',
        '-flatten',
        '-burn_sea',
        '-layer_def', json.dumps(LAYERS)]

```

What's important in the parameter file is the variables MP, TESTNAME and TARGS.
MP specifies how many simultaneous processes we want running.
TESTNAME states what test we want to run.
TARGS is the actual arguments for the script. Let's go through them one by one:

#### TILE_DB
This is the tile coverage database that indexes the pointcloud files.

#### OUTDIR
The directory where we want the output DSM and DTM tif files.

#### -dtm
Generate DTM.

#### -dsm
Generate DSM.

#### -overwrite
Overwrite any existing files in the OUTPUTDIR.

#### -hsys dvr90
States the height system of the pointcloud.
The pointcloud downloaded from Kortforsyningen is in dvr90, the Danish vertical frame of reference.

#### -nowarp
Output heights in the models in the same heightsystem as the pointcloud.
Leave ```-nowarp```out if the pointcloud is in ellipsoidal heights.

#### -clean_buildings
Remove low terrain points in buildings.
Applies only to DTM generation.

#### -triangle_limit 2.5
The largest side a triangle in water can have before it is flattened.
Applies only to DSM generation.

#### -zlim 0.4
Maximum height of triangles in water.

#### -flatten
Flattens water.

#### -burn_sea
Burns a constant sea level. Defaults to 0.0.

#### -layer_def json.dumps(LAYERS)
Layer definitions for each of the geometry tables we defined earlier in this text.
The layer definitions are expected to be in a JSON-format, that's why we have the json.dumps() call.
The real setup is made in the LAYERS variable, which is a python dictionary that can be translated to JSON.
We set up five layers: Lakes, lake_z, sea, rivers and buildings.
For each of them we supply af database connection string and a SQL query that selects the geometries that we want.
The SQL statements can be useful, like in that case of the rivers where we only want rivers of a certain width (> 2.5 m).
Finally we state the Z-attribute of the lake_z layer, so the script knows where to get the lake heigts from.

With the parameter file finished we can run the ```dem_gen_new``` script:

```
C:\dev\gstdhmqc> python qc_wrap.py C:\Temp\pc2dtm\dem_params.py
```

The script will take an hour or two to finish.
After the DTM and DSM has been created we want to move them around a little.
The a created in the same directory, and for practical reasons we want them in separate folders:

```
C:\Temp\pc2sql\dems> mkdir dtm
C:\Temp\pc2sql\dems> mkdir dsm
C:\Temp\pc2sql\dems>cp dtmdsm\dtm_*.tif dtm\
C:\Temp\pc2sql\dems>cp dtmdsm\dsm_*.tif dsm\
```

### Hillshades

The last step in this tutorial is to create hillshades from the freshly created DTM and DSM.
We use the ```hillshade.py``` script.
Again we are running it via the wrapper and thus need a tile index of the tif-files that make out the DTM and DSM:

```
C:\dev\gstdhmqc> python tile_coverage.py create C:\Temp\pc2dtm\dems\dtm tif C:\Temp\pc2dtm\dtm_coverage.sqlite
```

Now it's just a matter of calling the hillshade script via the wrapper:

```
C:\dev\gstdhmqc>python qc_wrap.py -testname hillshade -tiles C:\Temp\pc2dtm\dtm_coverage.sqlite -targs "-tiledb C:/temp/pc2dtm/dtm_coverage.sqlite C:/temp/pc2dtm/dems/hs_dtm"
```

At this point we have finished the work we have to do with DHMQC.
We have created a hillshaded DTM, but it is spread over a bunch of small tif-files.
In order to make the hillshades a bit easier to use, we create a VRT and add overviews to it:

```
C:\Temp\pc2dtm\dems>gdalbuildvrt hs_dtm.vrt hs_dtm\*.tif
0...10...20...30...40...50...60...70...80...90...100 - done.

C:\Temp\pc2dtm\dems>gdaladdo -ro hs_dtm.vrt 2 4 8 16
0...10...20...30...40...50...60...70...80...90...100 - done.
```

Similarly for the DSM:

```
C:\dev\gstdhmqc> python tile_coverage.py create C:\Temp\pc2dtm\dems\dsm tif C:\Temp\pc2dtm\dsm_coverage.sqlite

C:\dev\gstdhmqc>python qc_wrap.py -testname hillshade -tiles C:\Temp\pc2dtm\dsm_coverage.sqlite -targs "-tiledb C:/temp/pc2dtm/dsm_coverage.sqlite C:/temp/pc2dtm/dems/hs_dsm"

C:\Temp\pc2dtm\dems>gdalbuildvrt hs_dsm.vrt hs_dsm\*.tif
0...10...20...30...40...50...60...70...80...90...100 - done.

C:\Temp\pc2dtm\dems>gdaladdo -ro hs_dsm.vrt 2 4 8 16
0...10...20...30...40...50...60...70...80...90...100 - done.
```

Finally we are ready to view the hillshaded DTM and DSM with a GIS application!

## Conclusion

We have successfully generated DTM and DSM from a pointcloud by using supporting vector data.
We did that with by using a range of scripts from the DHMQC software package.

Finally we created hillshades of the DTM and DSM.

