import sys,os
import build
import shutil
import platform

BUILD_DIR=os.path.dirname(__file__)
SRC_DIR=os.path.realpath(os.path.join(BUILD_DIR,".."))
ROOT_DIR=os.path.realpath(os.path.join(SRC_DIR,".."))
LIB_DIR=(os.path.join(ROOT_DIR,"qc/lib"))
if not os.path.exists(LIB_DIR):
    os.mkdir(LIB_DIR)
else: 
    shutil.rmtree(LIB_DIR)
args=["",LIB_DIR]
#Input extra arguments e.g. to specify that you are using a 64-bit compiler: -x64, and /or using a special compiler e.g. -msvc, -cc clang, -sunc....
if len(sys.argv)>1:
	args.extend(sys.argv[1:])
build.main(args) #add extra compiler selection args... e.g. -msvc -cc clang etc...

