import sys,os,ctypes
import numpy as np
LIBDIR=os.path.realpath(os.path.join(os.path.dirname(__file__),"../lib"))
LIBNAME="libfgeom"
XY_TYPE=np.ctypeslib.ndpointer(dtype=np.float64,flags=['C','O','A'])
MASK_TYPE=np.ctypeslib.ndpointer(dtype=np.bool,ndim=1,flags=['C','O','A','W'])

LP_CINT=ctypes.POINTER(ctypes.c_int)
LP_CCHAR=ctypes.POINTER(ctypes.c_char)
lib=np.ctypeslib.load_library(LIBNAME, LIBDIR)
##############
## corresponds to
## array_geometry.h
##############
#void p_in_buf(double *p_in, char *mout, double *verts, unsigned long np, unsigned long nv, double d)
lib.p_in_buf.argtypes=[XY_TYPE,MASK_TYPE, XY_TYPE, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_double]
lib.p_in_buf.restype=None
lib.p_in_poly.argtypes=[XY_TYPE,MASK_TYPE, XY_TYPE, ctypes.c_ulong, ctypes.c_ulong]
lib.p_in_poly.restype=ctypes.c_int



def points_in_buffer(points, vertices, dist):
	out=np.empty((points.shape[0],),dtype=np.bool) #its a byte, really
	lib.p_in_buf(points,out,vertices,points.shape[0],vertices.shape[0],dist)
	return out


def points_in_polygon(points, vertices):
	if not (vertices[vertices.shape[0]-1]==vertices[0]).all():
		raise ValueError("Polygon boundary not closed!")
	out=np.empty((points.shape[0],),dtype=np.bool) #its a byte, really
	some=lib.p_in_poly(points,out,vertices,points.shape[0],vertices.shape[0])
	if some<0: #should not happen!
		print("Oh no - not closed!")
	return out


if __name__=="__main__":
	pts=np.asarray(((0.5,0.5),(2.5,3.5)),dtype=np.float64)
	verts=np.asarray(((0,0),(1,0),(1,1),(0,1),(0,0)),dtype=np.float64)
	M1=points_in_buffer(pts,verts,0.8)
	M2=points_in_polygon(pts,verts)
	print("Points in buffer: %s" %M1)
	print("Points in polygon: %s" %M2)
	