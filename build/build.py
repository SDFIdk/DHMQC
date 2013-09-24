import sys,os
from cc import *
from core import *


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
	ROOT_DIR=os.path.realpath(os.path.join(os.path.dirname(__file__),".."))
	LIB_TRI="libtri"
	SRC_TRI=[os.path.join(ROOT_DIR,"triangle","triangle.c")]
	LIB_INDEX="libtripy"
	SRC_INDEX=[os.path.join(ROOT_DIR,"triangle",x) for x in ["_tri.c","trig_index.c"]]
	LIB_SLASH="slash"
	SRC_SLASH=[os.path.join(ROOT_DIR,"slash","slashpy.c")]
	LIBS=[LIB_TRI,LIB_INDEX,LIB_SLASH]
	defines=["TRILIBRARY","NO_TIMER","POINTERS_ARE_VERY_LONG"]
	if "-x64" in args:
		LIBS=[x+"64" for x in LIBS]
		defines.append("POINTERS_ARE_VERY_LONG")
	if sys.platform.startswith("win"):
		dll=".dll"
		if "-msvc" in args:
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
	ok=Build(compiler,LIBS[1],SRC_INDEX,[],[],False,True,[LIBS[0]],def_file="libtripy.def",build_dir=build_dir,link_all=False)
	print("Succes: %s" %ok)
	if not ok:
		sys.exit(1)
	ok=Build(compiler,LIBS[2],SRC_SLASH,[],[],False,True,[],def_file="libslash.def",build_dir=build_dir,link_all=False)
	print("Succes: %s" %ok)
	
	
if __name__=="__main__":
	main(sys.argv)
	
	
	