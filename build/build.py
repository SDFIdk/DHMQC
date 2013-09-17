import sys,os
from cc import *
from core import *
compiler=SelectCompiler(sys.argv[2:])
print compiler
build_dir=os.path.realpath("./BUILD")
lib_dir=os.path.realpath(sys.argv[1])
DIR=os.path.realpath(os.path.join("..",os.path.dirname(__file__)))
LIB_TRI="libtri"
SRC_TRI=[os.path.join(DIR,"triangle","triangle.c")]
LIB_INDEX="libtripy"
SRC_INDEX=[os.path.join(DIR,"triangle",x) for x in ["_tri.c","trig_index.c"]]
LIB_SLASH="slash"
SRC_SLASH=[os.path.join(DIR,"slash","slashpy.c"]
LIBS=[LIB_TRI,LIB_INDEX,LIB_SLASH]
defines=["TRILIBRARY","NO_TIMER","POINTERS_ARE_VERY_LONG"]
if "-x64" in sys.argv:
	LIBS=[x+"64" for x in LIBS]
	defines.append("POINTERS_ARE_VERY_LONG")
if sys.platform.startswith("win"):
	dll=".dll"
	if "-msvc" in sys.argv:
		defines.append("CPU86")
	else:
		defines.append("GCC_FPU_CONTROL")
else:
	dll=".so"
LIBS=[os.path.realpath(os.path.join(lib_dir,x+dll)) for x in LIBS]
ok=Build(compiler,LIBS[0],SRC_TRI,[],defines,False,True,[],def_file="libtri.def",build_dir=build_dir,link_all=False)
print("Succes: %s" %ok)
if not ok:
	sys.exit(1)
ok=Build(compiler,LIBS[1],SRC_INDEX,[],[],False,True,[LIB_TRI],def_file="libtripy.def",build_dir=build_dir,link_all=False)
print("Succes: %s" %ok)
if not ok:
	sys.exit(1)
ok=Build(compiler,LIBS[2],SRC_SLASH,,[],[],False,True,[],def_file="libslash.def",build_dir=build_dir,link_all=False)
print("Succes: %s" %ok)