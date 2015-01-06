import sys,os,ctypes
import numpy as np
from osgeo import ogr
LIBDIR=os.path.realpath(os.path.join(os.path.dirname(__file__),"../lib"))
LIBNAME="libfgeom"
XY_TYPE=np.ctypeslib.ndpointer(dtype=np.float64,flags=['C','O','A','W'])
GRID_TYPE=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags=['C','O','A','W'])
Z_TYPE=np.ctypeslib.ndpointer(dtype=np.float64,ndim=1,flags=['C','O','A','W'])
MASK_TYPE=np.ctypeslib.ndpointer(dtype=np.bool,ndim=1,flags=['C','O','A','W'])
UINT32_TYPE=np.ctypeslib.ndpointer(dtype=np.uint32,ndim=1,flags=['C','O','A'])
HMAP_TYPE=np.ctypeslib.ndpointer(dtype=np.uint32,ndim=2,flags=['C','O','A'])
UINT8_VOXELS=np.ctypeslib.ndpointer(dtype=np.uint8,ndim=3,flags=['C','O','A','W'])
INT32_VOXELS=np.ctypeslib.ndpointer(dtype=np.int32,ndim=3,flags=['C','O','A','W'])
INT32_TYPE=np.ctypeslib.ndpointer(dtype=np.int32,ndim=1,flags=['C','O','A','W'])
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
lib.get_triangle_geometry.argtypes=[XY_TYPE,Z_TYPE,LP_CINT,np.ctypeslib.ndpointer(dtype=np.float32,ndim=2,flags=['C','O','A','W']),ctypes.c_int]
lib.get_triangle_geometry.restype=None
lib.mark_bd_vertices.argtypes=[MASK_TYPE,MASK_TYPE,LP_CINT,MASK_TYPE,ctypes.c_int,ctypes.c_int]
lib.mark_bd_vertices.restype=None
#int fill_spatial_index(int *sorted_flat_indices, int *index, int npoints, int max_index)
lib.fill_spatial_index.argtypes=[INT32_TYPE,INT32_TYPE, ctypes.c_int, ctypes.c_int]
lib.fill_spatial_index.restype=ctypes.c_int
lib.pc_min_filter.argtypes=[XY_TYPE,Z_TYPE, Z_TYPE, ctypes.c_double, INT32_TYPE, XY_TYPE, ctypes.c_int]
lib.pc_min_filter.restype=None
lib.pc_mean_filter.argtypes=[XY_TYPE,Z_TYPE, Z_TYPE, ctypes.c_double, INT32_TYPE, XY_TYPE, ctypes.c_int]
lib.pc_mean_filter.restype=None
lib.pc_spike_filter.argtypes=[XY_TYPE,Z_TYPE, Z_TYPE, ctypes.c_double, ctypes.c_double, ctypes.c_double, INT32_TYPE, XY_TYPE, ctypes.c_int]
lib.pc_spike_filter.restype=None
#void pc_noise_filter(double *pc_xy, double *pc_z, double *z_out, double filter_rad, double zlim, double den_cut, int *spatial_index, double *header, int npoints);
lib.pc_thinning_filter.argtypes=[XY_TYPE,Z_TYPE, Z_TYPE, ctypes.c_double, ctypes.c_double, ctypes.c_double, INT32_TYPE, XY_TYPE, ctypes.c_int]
lib.pc_thinning_filter.restype=None
lib.pc_isolation_filter.argtypes=[XY_TYPE,Z_TYPE, Z_TYPE, ctypes.c_double, ctypes.c_double, INT32_TYPE, XY_TYPE, ctypes.c_int]
lib.pc_isolation_filter.restype=None
lib.pc_wire_filter.argtypes=[XY_TYPE,Z_TYPE, Z_TYPE, ctypes.c_double, ctypes.c_double, INT32_TYPE, XY_TYPE, ctypes.c_int]
lib.pc_wire_filter.restype=None
lib.pc_correlation_filter.argtypes=[XY_TYPE,Z_TYPE, Z_TYPE, ctypes.c_double,Z_TYPE, INT32_TYPE, XY_TYPE, ctypes.c_int]
lib.pc_correlation_filter.restype=None
#binning
#void moving_bins(double *z, int *nout, double rad, int n);
lib.moving_bins.argtypes=[Z_TYPE,INT32_TYPE,ctypes.c_double,ctypes.c_int]
lib.moving_bins.restype=None
#a triangle based filter
#void tri_filter_low(double *z, double *zout, int *tri, double cut_off, int ntri)
lib.tri_filter_low.argtypes=[Z_TYPE,Z_TYPE,LP_CINT,ctypes.c_double,ctypes.c_int]
lib.tri_filter_low.restype=None
#hmap filler
#void fill_it_up(unsigned char *out, unsigned int *hmap, int rows, int cols, int stacks);
lib.fill_it_up.argtypes=[UINT8_VOXELS,HMAP_TYPE]+[ctypes.c_int]*3
lib.fill_it_up.restype=None
lib.find_floating_voxels.argtypes=[INT32_VOXELS,INT32_VOXELS]+[ctypes.c_int]*4
lib.find_floating_voxels.restype=None

def moving_bins(z,rad):
	#Will sort input -- so no need to do that first...
	zs=np.sort(z).astype(np.float64)
	n_out=np.zeros(zs.shape,dtype=np.int32)
	lib.moving_bins(zs,n_out,rad,zs.shape[0])
	return zs,n_out

def tri_filter_low(z,tri,ntri,cut_off):
	zout=np.copy(z)
	lib.tri_filter_low(z,zout,tri,cut_off,ntri)
	return zout
	



def ogrpoints2array(ogr_geoms):
	out=np.empty((len(ogr_geoms),3),dtype=np.float64)
	for i in xrange(len(ogr_geoms)):
		out[i,:]=ogr_geoms[i].GetPoint()
	return out
		

def ogrgeom2array(ogr_geom,flatten=True):
	t=ogr_geom.GetGeometryType()
	if t==ogr.wkbLineString or t==ogr.wkbLineString25D:
		return ogrline2array(ogr_geom,flatten)
	elif t==ogr.wkbPolygon or t==ogr.wkbPolygon25D:
		return ogrpoly2array(ogr_geom,flatten)
	else:
		raise Exception("Unsupported geometry type: %s" %ogr_geom.GetGeometryName())

def ogrpoly2array(ogr_poly,flatten=True):
	ng=ogr_poly.GetGeometryCount()
	rings=[]
	for i in range(ng):
		ring=ogr_poly.GetGeometryRef(i)
		arr=np.asarray(ring.GetPoints())
		if flatten and arr.shape[1]>2:
			arr=arr[:,0:2].copy()
		rings.append(arr)
	return rings

def ogrline2array(ogr_line,flatten=True):
	pts=ogr_line.GetPoints()
	#for an incompatible geometry ogr returns None... but does not raise a python error...!
	if pts is None:
		if flatten:
			return np.empty((0,2))
		else:
			return np.empty((0,3))
	arr=np.asarray(pts)
	if flatten and arr.shape[1]>2:
		arr=arr[:,0:2].copy()
	return arr

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
	bbox[0:2]=np.min(arr[:,:2],axis=0)
	bbox[2:4]=np.max(arr[:,:2],axis=0)
	return bbox


def points2ogr_polygon(points):
	#input an iterable of 2d 'points', slow interface for large collections...
	s=ogr.Geometry(ogr.wkbLineString)
	for p in points:
		s.AddPoint_2D(p[0],p[1])
	s.AddPoint_2D(points[0][0],points[0][1]) #close
	p=ogr.BuildPolygonFromEdges(ogr.ForceToMultiLineString(s))
	return p

def bbox_intersection(bbox1,bbox2):
	box=[-1,-1,-1,-1]
	box[0]=max(bbox1[0],bbox2[0])
	box[1]=max(bbox1[1],bbox2[1])
	box[2]=min(bbox1[2],bbox2[2])
	box[3]=min(bbox1[3],bbox2[3])
	if box[0]>=box[2] or box[1]>=box[3]:
		return None
	return box


def bbox_to_polygon(bbox):
	points=((bbox[0],bbox[1]),(bbox[2],bbox[1]),(bbox[2],bbox[3]),(bbox[0],bbox[3]))
	poly=points2ogr_polygon(points)
	return poly

def cut_geom_to_bbox(geom,bbox):
	#input a bounding box as returned from get_bounds...
	poly=bbox_to_polygon(bbox)
	return poly.Intersection(geom)


	
	
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

def get_boundary_vertices(validity_mask,poly_mask,triangles):
	out=np.empty_like(poly_mask)
	lib.mark_bd_vertices(validity_mask,poly_mask,triangles,out,validity_mask.shape[0],poly_mask.shape[0])
	return out




if __name__=="__main__":
	pts=np.asarray(((0.5,0.5),(2.5,3.5)),dtype=np.float64)
	verts=np.asarray(((0,0),(1,0),(1,1),(0,1),(0,0)),dtype=np.float64)
	M1=points_in_buffer(pts,verts,0.8)
	M2=points_in_polygon(pts,verts)
	print("Points in buffer: %s" %M1)
	print("Points in polygon: %s" %M2)
	