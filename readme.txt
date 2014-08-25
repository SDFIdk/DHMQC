Build instructions... 

- change directory to src/build

- from the shell run "python deploy.py"

- use -x64 to specify 64-bit build
  (your compiler will already do that, this will only change a few defines)

- use -msvc to build with Visual Studio command line tools.
  Run from a Visual Studio command shell (e.g."VS2014 x64 Cross Tools Command Prompt"
  from the start menu).
  Default compiler is some sort of gcc.

look at the example "test.py" in the folder "qc" for some basic commands.
