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

* [Tutorial: Pointcloud to DEMs](https://github.com/Kortforsyningen/DHMQC/blob/master/doc/howto_pc_to_dem.md)
* [Installation](https://github.com/Kortforsyningen/DHMQC/blob/master/doc/installation.md)
* [Details](https://github.com/Kortforsyningen/DHMQC/blob/master/doc/details.md)

### Build options ###

* If you experience problems building on OS X, it is most likely caused by clang.
  Note that the XCode gcc is just an alias for clang.
  Use gcc from another source, for instance Homebrew.

* use -msvc to build with Visual Studio command line tools.
  Run from a Visual Studio command shell (e.g."VS2014 x64 Cross Tools Command Prompt"
  from the start menu).
  Default compiler is some sort of gcc.

* use the -PG option to define a connection string to a PostGis-db for reporting results.

Detailed instructions can be found in the [installation guide](https://github.com/Kortforsyningen/DHMQC/blob/master/doc/installation.md)


## Testing ###

The testsuite can be invoked by:

```
python test_suite.py
```
