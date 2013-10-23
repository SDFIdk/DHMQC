import sys,os,ctypes,time
import numpy as np
LIBDIR=os.path.realpath(os.path.join(os.path.dirname(__file__),"../lib"))
LIBNAME="libfgeom"
if sys.platform.startswith("win"):
	LIBNAME+=".dll"
	os.environ["PATH"]+=";"+LIBDIR
elif "darwin" in sys.platform:
	LIBNAME+=".dylib"
else:
	LIBNAME+=".so"
LP_CDOUBLE=ctypes.POINTER(ctypes.c_double)
LP_CINT=ctypes.POINTER(ctypes.c_int)
LP_CCHAR=ctypes.POINTER(ctypes.c_char)
lib_name=os.path.join(LIBDIR,LIBNAME)
lib=ctypes.cdll.LoadLibrary(lib_name)
##############
##corresponds to
##array_geometry.h
##############
#void p_in_buf(double *p_in, char *mout, double *verts, unsigned long np, unsigned long nv, double d)
lib.p_in_buf.argtypes=[LP_CDOUBLE,LP_CCHAR, LP_CDOUBLE, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_double]
lib.p_in_buf.restype=None
lib.p_in_poly.argtypes=[LP_CDOUBLE,LP_CCHAR, LP_CDOUBLE, ctypes.c_ulong, ctypes.c_ulong]
lib.p_in_poly.restype=ctypes.c_int



def points_in_buffer(points, vertices, dist):
	out=np.empty((points.shape[0],),dtype=np.bool) #its a byte, really
	lib.p_in_buf(points.ctypes.data_as(LP_CDOUBLE),out.ctypes.data_as(LP_CCHAR),vertices.ctypes.data_as(LP_CDOUBLE),points.shape[0],vertices.shape[0],dist)
	return out


def points_in_polygon(points, vertices):
	if not (vertices[vertices.shape[0]-1]==vertices[0]).all():
		vertices=np.vstack((vertices,vertices[0]))
	print vertices.flags
	out=np.empty((points.shape[0],),dtype=np.bool) #its a byte, really
	some=lib.p_in_poly(points.ctypes.data_as(LP_CDOUBLE),out.ctypes.data_as(LP_CCHAR),vertices.ctypes.data_as(LP_CDOUBLE),points.shape[0],vertices.shape[0])
	if some<0: #should not happen!
		print("Oh no - not closed!")
	return out

