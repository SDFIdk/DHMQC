# DHMQC #

Analysis and processing of LIDAR point cloud data.
The DHMQC software package has been developed as a part of the nation-wide update of the Danish Elevation Model,
DK-DEM (DHM).
DHMQC has three main purposes: Data quality control, point cloud manipulation and production of derived datasets.
Included is an extensive set of geometry checks that enables you to automatically quantify precision and
accuracy errors in a nation-wide pointcloud.
DHMQC also has tools for systematic reclassification of the point cloud and patching of areas with no data coverage.
Derived datasets suchs as DEMs and vector geometries can be extracted from a point cloud by DHMQC.

## Requirements ##

DHMQC is currently supported on Windows and Linux, with Python versions 3.9 and 3.10. The recommended way of installing DHMQC is using a Conda environment.

Installation requires a C and C++ compiler. Currently, only `gcc`/`g++` are supported (on Windows via MinGW-w64).

Detailed instructions can be found in the [installation guide](doc/installation.md).

## Quick start ##

* [Installation](doc/installation.md)
* [Tutorial: Pointcloud to DEMs](doc/howto_pc_to_dem.md)
* [Details](doc/details.md)
