Build instructions... 

- change directory to src/build

- from the shell run "python build.py"

- use -x64 to specify 64-bit build
  (your compiler will already do that, this will only change a few defines)

- use -msvc to build with Visual Studio command line tools.
  Run from a Visual Studio command shell (e.g."VS2014 x64 Cross Tools Command Prompt"
  from the start menu).
  Default compiler is some sort of gcc.

- use the -PG option to define a connection string to a PostGis-db for reporting results.

A template for adding a new test, ready for wrapping in qc_wrap, can be found in qc/template.py

Testsuite can be invoked by: python test_suite.py

More information is available in the wiki pages.