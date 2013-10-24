import sys,os,ctypes
import numpy as np
LIBDIR=os.path.realpath(os.path.join(os.path.dirname(__file__),"../lib"))
LIBNAME="libfgeom"
XY_TYPE=np.ctypeslib.ndpointer(dtype=np.float64,flags=['C','O','A'])
Z_TYPE_IN=np.ctypeslib.ndpointer(dtype=np.float64,ndim=1,flags=['C','O','A'])
MASK_TYPE=np.ctypeslib.ndpointer(dtype=np.bool,ndim=1,flags=['C','O','A','W'])
UINT32_TYPE=np.ctypeslib.ndpointer(dtype=np.uint32,ndim=1,flags=['C','O','A'])
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
lib.p_in_poly.argtypes=[XY_TYPE,MASK_TYPE, XY_TYPE, ctypes.c_uint, UINT32_TYPE, ctypes.c_uint]
lib.p_in_poly.restype=ctypes.c_int
lib.get_triangle_geometry.argtypes=[XY_TYPE,Z_TYPE_IN,LP_CINT,np.ctypeslib.ndpointer(dtype=np.float32,ndim=2,flags=['C','O','A','W']),ctypes.c_int]
lib.get_triangle_geometry.restype=None


def ogrpoly2array(ogr_poly):
	ng=ogr_poly.GetGeometryCount()
	rings=[]
	for i in range(ng):
		ring=ogr_poly.GetGeometryRef(i)
		rings.append(np.asarray(ring.GetPoints()))
	return rings

def ogrline2array(ogr_line):
	return np.asarray(ogr_line.GetPoints())

def points_in_buffer(points, vertices, dist):
	out=np.empty((points.shape[0],),dtype=np.bool) #its a byte, really
	lib.p_in_buf(points,out,vertices,points.shape[0],vertices.shape[0],dist)
	return out

def get_triangle_geometry(xy,z,triangles,n_triangles):
	out=np.empty((n_triangles,3),dtype=np.float32)
	lib.get_triangle_geometry(xy,z,triangles,out,n_triangles)
	return out

def get_bounds(geom):
	if isinstance(geom,list):
		arr=geom[0]
	else:
		arr=geom
	bbox=np.empty((4,),dtype=np.float64)
	bbox[0:2]=np.min(arr,axis=0)
	bbox[2:4]=np.max(arr,axis=0)
	return bbox

def points_in_polygon(points, rings):
	verts=np.empty((0,2),dtype=np.float64)
	nv=[]
	for ring in rings:
		if not (ring[-1]==ring[0]).all():
			raise ValueError("Polygon boundary not closed!")
		verts=np.vstack((verts,ring))
		nv.append(ring.shape[0])
	nv=np.asarray(nv,dtype=np.uint32)
	out=np.empty((points.shape[0],),dtype=np.bool) #its a byte, really
	some=lib.p_in_poly(points,out,verts,points.shape[0],nv,len(rings))
	return out


if __name__=="__main__":
	pts=np.asarray(((0.5,0.5),(2.5,3.5)),dtype=np.float64)
	verts=np.asarray(((0,0),(1,0),(1,1),(0,1),(0,0)),dtype=np.float64)
	M1=points_in_buffer(pts,verts,0.8)
	M2=points_in_polygon(pts,verts)
	print("Points in buffer: %s" %M1)
	print("Points in polygon: %s" %M2)
	