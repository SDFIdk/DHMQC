import sys,os
from cc import *
from core import *
import platform
ROOT_DIR=os.path.realpath(os.path.join(os.path.dirname(__file__),".."))
LIB_TRI="libtri"
SRC_TRI=[os.path.join(ROOT_DIR,"triangle","triangle.c")]
LIB_INDEX="libtripy"
SRC_INDEX=[os.path.join(ROOT_DIR,"triangle",x) for x in ["_tri.c","trig_index.c"]]
LIB_SLASH="slash"
SRC_SLASH=[os.path.join(ROOT_DIR,"slash","slashpy.c")]
LIBS=[LIB_TRI,LIB_INDEX,LIB_SLASH]
TRI_DEFINES=["TRILIBRARY","NO_TIMER"]
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
		TRI_DEFINES.append("POINTERS_ARE_VERY_LONG")
	elif "64" in platform.architecture()[0]:
		print("WARNING: you're running 64-bit python but haven't specified a 64-bit build ( -x64 ) !")
	
	if sys.platform.startswith("win"):
		if "-msvc" in args:
			TRI_DEFINES.append("CPU86")
		else:
			pass
			#TRI_DEFINES.append("GCC_FPU_CONTROL")
	
	libs=[os.path.realpath(os.path.join(lib_dir,x+DLL)) for x in LIBS]
	ok=Build(compiler,libs[0],SRC_TRI,[],TRI_DEFINES,False,True,[],def_file="libtri.def",build_dir=build_dir,link_all=False)
	print("Succes: %s" %ok)
	if not ok:
		sys.exit(1)
	ok=Build(compiler,libs[1],SRC_INDEX,[],[],False,True,[libs[0]],def_file="libtripy.def",build_dir=build_dir,link_all=False)
	print("Succes: %s" %ok)
	if not ok:
		sys.exit(1)
	ok=Build(compiler,libs[2],SRC_SLASH,[],[],False,True,[],def_file="libslash.def",build_dir=build_dir,link_all=False)
	print("Succes: %s" %ok)
	
	
if __name__=="__main__":
	main(sys.argv)
	
	
	