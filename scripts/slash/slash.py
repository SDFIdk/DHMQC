import sys,os,ctypes,platform
import numpy as np
LIBDIR=os.path.realpath(os.path.join(os.path.dirname(__file__),"../lib"))
LIBNAME="slash"
#'64' not appended to libname anymore
if sys.platform.startswith("win"):
	LIBNAME+=".dll"
	os.environ["PATH"]+=";"+LIBDIR
elif "darwin" in sys.platform:
	LIBNAME+=".dylib"
else:
	LIBNAME+=".so"

LP_CDOUBLE=ctypes.POINTER(ctypes.c_double)
LP_CINT=ctypes.POINTER(ctypes.c_int)
#lib_name=os.path.join(os.path.dirname(__file__),LIBNAME)
lib_name=os.path.join(LIBDIR,LIBNAME)
print("Loading %s" %lib_name)
lib=ctypes.cdll.LoadLibrary(lib_name)
lib.las_open.argtypes=[ctypes.c_char_p,ctypes.c_char_p]
lib.las_open.restype=ctypes.c_void_p
lib.las_close.argtypes=[ctypes.c_void_p]
lib.las_close.restype=None
lib.py_get_num_records.argtypes=[ctypes.c_void_p]
lib.py_get_num_records.restype=ctypes.c_ulong
lib.py_get_records.argtypes=[ctypes.c_void_p,LP_CDOUBLE,LP_CDOUBLE,LP_CINT,LP_CINT,ctypes.c_ulong]
lib.py_get_records.restype=ctypes.c_ulong

class LasFile(object):
	def __init__(self,path):
		self.plas=lib.las_open(path,"rb")
		if self.plas is None:
			raise ValueError("Failed to open input file...")
		self.n_records=lib.py_get_num_records(self.plas)
		self.path=path
	def close(self):
		if self.plas is not None:
			lib.las_close(self.plas)
	def get_number_of_records(self):
		return self.n_records
	def read_records(self,n=-1):
		if (n==-1):
			n=self.n_records
		else:
			n=min(n,self.n_records)
		xy=np.empty((n,2),dtype=np.float64)
		z=np.empty((n,),dtype=np.float64)
		c=np.empty((n,),dtype=np.int32)
		pid=np.empty((n,),dtype=np.int32)
		n_read=lib.py_get_records(self.plas,xy.ctypes.data_as(LP_CDOUBLE),z.ctypes.data_as(LP_CDOUBLE),c.ctypes.data_as(LP_CINT),pid.ctypes.data_as(LP_CINT),n)
		print "Read:",n_read
		return xy,z,c,pid

if __name__=="__main__":
	lasf=LasFile(sys.argv[1])
	print("%d points in %s" %(lasf.get_number_of_records(),sys.argv[1]))
	xy,z,c,pid=lasf.read_records()
	x1,y1=xy.min(axis=0)
	x2,y2=xy.max(axis=0)
	z1=z.min()
	z2=z.max()
	print("XY: %.2f %.2f %.2f %.2f, Z: %.2f %.2f %.2f" %(x1,y1,x2,y2,z1,z2,z.mean()))
	print("classes: %s" %np.unique(c))
	print("point ids: %s" %np.unique(pid))
	
