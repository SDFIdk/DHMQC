import sys,os
from cc import *
from core import *
import platform
ROOT_DIR=os.path.realpath(os.path.join(os.path.dirname(__file__),".."))
#output binaries and source input defined here
INC_HELIOS=[os.path.join(ROOT_DIR,"helios","include")]
#triangle
LIB_TRI="libtri"
SRC_TRI=[os.path.join(ROOT_DIR,"triangle","triangle.c")]
TRI_DEFINES=["TRILIBRARY","NO_TIMER"]
DEF_TRI="libtri.def"
#spatial indexing
LIB_INDEX="libtripy"
SRC_INDEX=[os.path.join(ROOT_DIR,"triangle",x) for x in ["_tri.c","trig_index.c"]]
DEF_INDEX="libtripy.def"
#slash
LIB_SLASH="slash"
SRC_SLASH=[os.path.join(ROOT_DIR,"etc","slashpy.c")]
DEF_SLASH="libslash.def"
#array geometry
LIB_GEOM="libfgeom"
SRC_GEOM=[os.path.join(ROOT_DIR,"geometry","array_geometry.c")]
DEF_GEOM="libfgeom.def"
#page
PAGE_EXE="page"
SRC_PAGE=[os.path.join(ROOT_DIR,"helios","src","page.c")]

class BuildObject(object):
	def __init__(self,name,source,include=[],defines=[],link=[],def_file="", is_library=True):
		self.name=name
		self.source=source
		self.include=include
		self.defines=defines
		self.link=link
		self.def_file=def_file
		self.is_library=is_library #else exe
		if is_library:
			self.extension=DLL
		else:
			self.extension=EXE
	def get_build_name(self,out_path=""):
		return os.path.join(out_path,self.name)+self.extension
		
#and now REALLY specify what to build
OLIB_SLASH=BuildObject(LIB_SLASH,SRC_SLASH,INC_HELIOS,def_file=DEF_SLASH)
OLIB_TRI=BuildObject(LIB_TRI,SRC_TRI,defines=TRI_DEFINES,def_file=DEF_TRI)
OLIB_INDEX=BuildObject(LIB_INDEX,SRC_INDEX,link=[OLIB_TRI],def_file=DEF_INDEX)
OLIB_GEOM=BuildObject(LIB_GEOM,SRC_GEOM,def_file=DEF_GEOM)
OPAGE_EXE=BuildObject(PAGE_EXE,SRC_PAGE,INC_HELIOS,is_library=False)
TO_BUILD=[OLIB_SLASH,OLIB_TRI,OLIB_INDEX,OLIB_GEOM,OPAGE_EXE]


def main (args):
	if len(args)<2:
		print("Usage: %s <out_dir> <compiler_selection_args> ..." %os.path.basename(args[0]))
		sys.exit()
	compiler=SelectCompiler(args[2:])
	print("Selecting compiler: %s" %compiler)
	build_dir=os.path.realpath("./BUILD")
	lib_dir=os.path.realpath(args[1])
	if not os.path.exists(lib_dir):
		os.mkdir(lib_dir)
	if "-x64" in args:
		OLIB_TRI.defines.append("POINTERS_ARE_VERY_LONG")
	elif "64" in platform.architecture()[0]:
		print("WARNING: you're running 64-bit python but haven't specified a 64-bit build ( -x64 ) !")
	
	if sys.platform.startswith("win"):
		if "-msvc" in args:
			OLIB_TRI.defines.append("CPU86")
		else:
			pass
			#TRI_DEFINES.append("GCC_FPU_CONTROL")
	is_debug="-debug" in args
	print("Building....")
	sl="*"*50
	for out in TO_BUILD:
		print("%s\nBuilding: %s\n%s" %(sl, out.name,sl))
		link=[x.get_build_name(lib_dir) for x in out.link]
		ok=Build(compiler,out.get_build_name(lib_dir),out.source,out.include,out.defines,is_debug,out.is_library,link,out.def_file,build_dir=build_dir,link_all=False)
		print("Succes: %s" %ok)
		if not ok:
			sys.exit(1)
	
	
	
if __name__=="__main__":
	main(sys.argv)
	
	
	