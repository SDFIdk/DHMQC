# DHMQC #

## Quick start ##

[Tutorial: Pointcloud to DEMs](https://bitbucket.org/GSTudvikler/gstdhmqc/src/tip/doc/howto_pc_to_dem.md?at=default&fileviewer=file-view-default)

## Build instructions ##

1. change directory to src/build

2. from the shell run "python build.py"

3. use -x64 to specify 64-bit build
  (your compiler will already do that, this will only change a few defines)

4. use -msvc to build with Visual Studio command line tools.
  Run from a Visual Studio command shell (e.g."VS2014 x64 Cross Tools Command Prompt"
  from the start menu).
  Default compiler is some sort of gcc.

5. use the -PG option to define a connection string to a PostGis-db for reporting results.

A template for adding a new test, ready for wrapping in qc_wrap, can be found in qc/template.py

## Testing

Testsuite can be invoked by: python test_suite.py

## Further information

More information is available in the [wiki pages](https://bitbucket.org/GSTudvikler/gstdhmqc/wiki/Home).
