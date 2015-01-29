import sys,os
import platform
import shutil
import tempfile
import urllib2
import zipfile
import md5
import argparse
from cc import *
from core import *
HERE=os.getcwd()
ROOT_DIR=os.path.realpath(os.path.join(os.path.dirname(__file__),".."))
#output binaries and source input defined here
BIN_DIR=os.path.join(ROOT_DIR,"..","qc","lib")
if not os.path.exists(BIN_DIR):
	os.mkdir(BIN_DIR)
INC_HELIOS=[os.path.join(ROOT_DIR,"helios","include")]
#triangle
LIB_TRI="libtri"
DIR_TRI=os.path.join(ROOT_DIR,"triangle")
PATCH_TRIANGLE=os.path.join(ROOT_DIR,"triangle","triangle_patch.diff")
URL_TRIANGLE="http://www.netlib.org/voronoi/triangle.zip"
TRI_DEFINES=["TRILIBRARY","NO_TIMER"]
MD5_TRI="Yjh\xfe\x94o)5\xcd\xff\xb1O\x1e$D\xc4"
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
#grid stuff - TODO: add more functionality (e.g. esrigrid.h)...
LIB_GRID="libgrid"
SRC_GRID=[os.path.join(ROOT_DIR,"etc","grid_stuff.c")]
#page
PAGE_EXE="page"
SRC_PAGE=[os.path.join(ROOT_DIR,"helios","src","page.c")]
PG_CONNECTION_FILE=os.path.join(ROOT_DIR,"..","qc","thatsDEM","pg_connection.py")


def is_newer(p1,p2):
	if not os.path.exists(p1):
		return False
	if not os.path.exists(p2):
		return True
	return os.path.getmtime(p1)>os.path.getmtime(p2)

class BuildObject(object):
	def __init__(self,name,outdir,source,include=[],defines=[],link=[],def_file="", is_library=True):
		self.name=name
		self.source=source
		self.include=include
		self.defines=defines
		self.link=link # a list of other build objects...
		self.def_file=def_file
		self.is_library=is_library #else exe
		self.needs_rebuild=False
		if is_library:
			self.extension=DLL
		else:
			self.extension=EXE
		self.outname=os.path.join(outdir,self.name)+self.extension
	def set_needs_rebuild(self,dep_files=[]):
		#just set this var in the dependency order of mutually dependent builds...
		self.needs_rebuild=False
		for s in self.source+[self.def_file]+dep_files:
			if is_newer(s,self.outname):
				self.needs_rebuild=True
				return
		for n in self.link:
			if isinstance(n,BuildObject) and n.needs_rebuild:
				self.needs_rebuild=True
				return
		


		
#and now REALLY specify what to build
OLIB_SLASH=BuildObject(LIB_SLASH,BIN_DIR,SRC_SLASH,INC_HELIOS,def_file=DEF_SLASH)
OLIB_TRI=BuildObject(LIB_TRI,BIN_DIR,[],defines=TRI_DEFINES,def_file=DEF_TRI)
OLIB_INDEX=BuildObject(LIB_INDEX,BIN_DIR,SRC_INDEX,link=[OLIB_TRI],def_file=DEF_INDEX)
OLIB_GEOM=BuildObject(LIB_GEOM,BIN_DIR,SRC_GEOM,def_file=DEF_GEOM)
OLIB_GRID=BuildObject(LIB_GRID,BIN_DIR,SRC_GRID)
OPAGE_EXE=BuildObject(PAGE_EXE,BIN_DIR,SRC_PAGE,INC_HELIOS,is_library=False)
TO_BUILD=[]

def patch_triangle():
	print("Starting patching process of triangle...")
	tmpdir=tempfile.mkdtemp()
	os.chdir(tmpdir)
	print("Downloading triangle...")
	try:
		with open("triangle.zip", 'wb') as f:
			response = urllib2.urlopen(URL_TRIANGLE)
			assert(response.getcode()==200)
			f.write(response.read())
		print("Done...")
		zf=zipfile.ZipFile("triangle.zip")
		zf.extract("triangle.c")
		zf.extract("triangle.h")
		print("Checking md5 sum of downloaded file...")
		with open("triangle.c","rb") as f:
			m5=md5.new(f.read()).digest()
		zf.close()
		assert(m5==MD5_TRI)
		print("ok...")
		run_cmd(["hg","init"])
		run_cmd(["hg","add","triangle.c"])
		run_cmd(["hg","commit","-m","dummy","-u","dummy"])
		rc,out=run_cmd(["hg","patch",PATCH_TRIANGLE])
		assert(rc==0)
		print("Copying files...")
		SRC_TRI=os.path.join(DIR_TRI,"triangle_p.c")
		shutil.copy("triangle.c",SRC_TRI)
		shutil.copy("triangle.h",os.path.join(DIR_TRI,"triangle_p.h"))
		os.chdir(HERE)
	except Exception,e:
		print("Patching process failed with error:\n"+str(e))
		rc=False
	else:
		OLIB_TRI.source=[SRC_TRI]
		rc=True
	try:
		shutil.rmtree(tmpdir)
	except Exception, e:
		print("Failed to delete temporary directory: "+tmpdir+"\n"+str(e))
	return rc



#Additional args which are not compiler selection args:
ARGS={"-PG":{"help":"Specify PostGis connection if you want to use a PG-db for reporting."},
"-debug":{"help":"Do a debug build.","action":"store_true"},
"-force":{"help":"Force a full rebuild.","action":"store_true"}
}

def main (args):
	parser=argparse.ArgumentParser(description="Build and setup script for dhmqc repository. Will be default try to build with gcc.")
	ARGS.update(COMPILER_SELECTION_OPTS)
	for key in ARGS:
		parser.add_argument(key,**ARGS[key])
	#some of the ARGS are not compiler selection args, but can be safely passed on to select_compiler which only checks for the relevant ones...
	pargs=parser.parse_args(args[1:])
	compiler=select_compiler(args[1:])
	print("Selecting compiler: %s" %compiler)
	build_dir=os.path.realpath("./BUILD")
	#First decide if we need to rebuild triangle
	to_build=[]
	OLIB_TRI.set_needs_rebuild([PATCH_TRIANGLE])
	OLIB_TRI.needs_rebuild|=pargs.force
	if OLIB_TRI.needs_rebuild:
		ok=patch_triangle()
		if not ok:
			print("Unable to patch triangle..Aborting...")
			sys.exit(1)
	if pargs.x64:
		#set our 64-bit patch define
		OLIB_TRI.defines.append("POINTERS_ARE_VERY_LONG")
	elif "64" in platform.architecture()[0]:
		print("WARNING: you're running 64-bit python but haven't specified a 64-bit build ( -x64 ) !")
	if IS_WINDOWS:
		if compiler.IS_MSVC:
			#another define which should (probably) be set for MSVC-compilers
			OLIB_TRI.defines.append("CPU86")
		else:
			pass #TODO: talk to thokn
			#TRI_DEFINES.append("GCC_FPU_CONTROL")
	is_debug="-debug" in args
	for out in [OLIB_INDEX,OLIB_SLASH,OLIB_GEOM,OLIB_GRID,OPAGE_EXE]:
		out.set_needs_rebuild()
		out.needs_rebuild|=pargs.force
	sl="*"*50
	for out in [OLIB_TRI,OLIB_INDEX,OLIB_SLASH,OLIB_GEOM,OLIB_GRID,OPAGE_EXE]:
		if not out.needs_rebuild:
			print("%s\n%s does not need a rebuild. Use -force to force a rebuild.\n%s" %(sl, out.name,sl))
			continue
		print("%s\nBuilding: %s\n%s" %(sl, out.name,sl))
		link=[x.outname for x in out.link]
		try:
			ok=build(compiler,out.outname,out.source,out.include,out.defines,is_debug,out.is_library,link,out.def_file,build_dir=build_dir,link_all=False)
		except Exception,e:
			print("Error: "+str(e)+"\n")
			print("*** MOST LIKELY the selected compiler is not available in the current environment. ***")
			sys.exit(1)
		print("Succes: %s" %ok)
		if not ok:
			sys.exit(1)
	if pargs.PG is not None:
		print("Writing pg-connection to "+PG_CONNECTION_FILE)
		with open(PG_CONNECTION_FILE,"w") as f:
			f.write('PG_CONNECTION="PG: '+pargs.PG+'"'+'\n')
	
		
	
	
	
if __name__=="__main__":
	main(sys.argv)
	
	
	