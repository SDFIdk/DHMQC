# DHMQC #

Analysis and processing of LIDAR point cloud data.
The DHMQC software package has been developed as a part of the nation-wide update of the Danish Elevation Model,
DK-DEM (DHM).
DHMQC has three main purposes: Data quality control, point cloud manipulation and production of derived datasets.
Included is an extensive set of geometry checks that enables you to automatically quantify precision and
accuracy errors in a nation-wide pointcloud.
DHMQC also has tools for systematic reclassification of the point cloud and patching of areas with no data coverage.
Derived datasets suchs as DEMs and vector geometries can be extracted from a point cloud by DHMQC.

## Quick start ##

* [Tutorial: Pointcloud to DEMs](doc/howto_pc_to_dem.md)
* [Installation](doc/installation.md)
* [Details](doc/details.md)

### Build options ###

* If you experience problems building on OS X, it is most likely caused by clang.
  Note that the XCode gcc is just an alias for clang.
  Use gcc from another source, for instance Homebrew.

* use the -PG option to define a connection string to a PostGis-db for reporting results.

Detailed instructions can be found in the [installation guide](doc/installation.md).
