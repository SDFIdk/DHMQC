# Copyright (c) 2015, Danish Geodata Agency <gst@gst.dk>
# 
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
import sys,os,ctypes,time
import numpy as np
LIBDIR=os.path.realpath(os.path.join(os.path.dirname(__file__),"../lib"))

LIBNAME="libtripy"
#'64' not appended to libname anymore
if sys.platform.startswith("win"):
	LIBNAME+=".dll"
	os.environ["PATH"]+=";"+LIBDIR
elif "darwin" in sys.platform:
	LIBNAME+=".dylib"
else:
	LIBNAME+=".so"
LP_CDOUBLE=ctypes.POINTER(ctypes.c_double)
LP_CFLOAT=ctypes.POINTER(ctypes.c_float)
LP_CINT=ctypes.POINTER(ctypes.c_int)
LP_CCHAR=ctypes.POINTER(ctypes.c_char)
#lib_name=os.path.join(os.path.dirname(__file__),LIBNAME)
lib_name=os.path.join(LIBDIR,LIBNAME)
#print("Loading %s" %lib_name)
lib=ctypes.cdll.LoadLibrary(lib_name)
lib.use_triangle.restype=LP_CINT
lib.use_triangle.argtypes=[LP_CDOUBLE,ctypes.c_int,LP_CINT]
lib.free_vertices.restype=None
lib.free_vertices.argtypes=[LP_CINT]
lib.free_index.restype=None
lib.free_index.argtypes=[ctypes.c_void_p]
lib.find_triangle.restype=None
lib.find_triangle.argtypes=[LP_CDOUBLE,LP_CINT,LP_CDOUBLE,LP_CINT,ctypes.c_void_p,LP_CCHAR,ctypes.c_int]
#void find_appropriate_triangles(double *pts, int *out, double *base_pts, double *base_z, int *tri, spatial_index *ind, int np, double tol_xy, double tol_z);
lib.inspect_index.restype=None
lib.inspect_index.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int]
lib.build_index.restype=ctypes.c_void_p
lib.build_index.argtypes=[LP_CDOUBLE,LP_CINT,ctypes.c_double,ctypes.c_int,ctypes.c_int]
#interpolate2(double *pts, double *base_pts, double *base_z, double *out, int *tri, spatial_index *ind, int np)
lib.interpolate.argtypes=[LP_CDOUBLE,LP_CDOUBLE,LP_CDOUBLE,LP_CDOUBLE,ctypes.c_double,LP_CINT,ctypes.c_void_p,LP_CCHAR,ctypes.c_int]
lib.interpolate.restype=None
#void make_grid(double *base_pts,double *base_z, int *tri, float *grid, float tgrid, double nd_val, int ncols, int nrows, double cx, double cy, double xl, double yu, spatial_index *ind)
lib.make_grid.argtypes=[LP_CDOUBLE,LP_CDOUBLE,LP_CINT,LP_CFLOAT,LP_CFLOAT,ctypes.c_float,ctypes.c_int,ctypes.c_int]+[ctypes.c_double]*4+[ctypes.c_void_p]
lib.make_grid.restype=None
#void make_grid_low(double *base_pts,double *base_z, int *tri, float *grid,  float nd_val, int ncols, int nrows, double cx, double cy, double xl, double yu, double cut_off, spatial_index *ind)
lib.make_grid_low.argtypes=[LP_CDOUBLE,LP_CDOUBLE,LP_CINT,LP_CFLOAT,ctypes.c_float,ctypes.c_int,ctypes.c_int]+[ctypes.c_double]*5+[ctypes.c_void_p]
lib.make_grid_low.restype=None
lib.get_triangles.argtypes=[LP_CINT,LP_CINT,LP_CINT,ctypes.c_int,ctypes.c_int]
lib.get_triangles.restype=None
lib.optimize_index.argtypes=[ctypes.c_void_p]
lib.optimize_index.restype=None
#void get_triangle_centers(double *xy, int *triangles, double *out, int n_trigs)
lib.get_triangle_centers.argtypres=[LP_CDOUBLE,LP_CINT,LP_CDOUBLE,ctypes.c_int]

class Triangulation(object):
	"""Triangulation class inspired by scipy.spatial.Delaunay
	Uses Triangle to do the hard work. Automatically builds an index.
	"""
	def __init__(self,points,cs=-1):
		self.vertices=None
		self.index=None
		self.validate_points(points)
		self.points=points
		nt=ctypes.c_int(0)
		self.vertices=lib.use_triangle(points.ctypes.data_as(LP_CDOUBLE),points.shape[0],ctypes.byref(nt))
		self.ntrig=nt.value
		#print("Triangles: %d" %self.ntrig)
		t1=time.clock()
		self.index=lib.build_index(points.ctypes.data_as(LP_CDOUBLE),self.vertices,cs,points.shape[0],self.ntrig)
		if self.index is None:
			raise Exception("Failed to build index...")
		t2=time.clock()
		#print("Index: %.5fs" %(t2-t1))
		self.transform=None #can be used to speed up things even more....
	def __del__(self):
		"""Destructor"""
		lib.free_vertices(self.vertices)
		lib.free_index(self.index)
	
	def validate_points(self,points,ndim=2,dtype=np.float64):
		#ALL this stuff is not needed if we use numpys ctypeslib interface - TODO.
		if not isinstance(points,np.ndarray):
			raise ValueError("Input points must be a Numpy ndarray")
		ok=points.flags["ALIGNED"] and points.flags["C_CONTIGUOUS"] and points.flags["OWNDATA"] and points.dtype==dtype
		if (not ok):
			raise ValueError("Input points must have flags 'ALIGNED','C_CONTIGUOUS','OWNDATA' and data type %s" %dtype)
		#TODO: figure out something useful here....	
		if points.ndim!=ndim or (ndim==2 and points.shape[1]!=2):
			raise ValueError("Bad shape of input - points:(n,2) z: (n,), indices: (n,)")
	def interpolate(self,z_base,xy_in,nd_val=-999,mask=None):
		"""Barycentric interpolation of input points xy_in based on values z_base in vertices. Points outside triangulation gets nd_val"""
		self.validate_points(xy_in)
		self.validate_points(z_base,1)
		if z_base.shape[0]!=self.points.shape[0]:
			raise ValueError("There must be exactly the same number of input zs as the number of triangulated points.")
		if mask is not None:
			if mask.shape[0]!=self.ntrig:
				raise ValueError("Validity mask size differs from number of triangles")
			self.validate_points(mask,ndim=1,dtype=np.bool)
			pmask=mask.ctypes.data_as(LP_CCHAR)
		else:
			pmask=None
		out=np.empty((xy_in.shape[0],),dtype=np.float64)
		lib.interpolate(xy_in.ctypes.data_as(LP_CDOUBLE),self.points.ctypes.data_as(LP_CDOUBLE),z_base.ctypes.data_as(LP_CDOUBLE),
		out.ctypes.data_as(LP_CDOUBLE),nd_val,self.vertices,self.index,pmask,xy_in.shape[0])
		return out
	
	def make_grid(self,z_base,ncols,nrows,xl,cx,yu,cy,nd_val=-999,return_triangles=False):
		#void make_grid(double *base_pts,double *base_z, int *tri, double *grid, double nd_val, int ncols, int nrows, double cx, double cy, double xl, double yu, spatial_index *ind)
		if z_base.shape[0]!=self.points.shape[0]:
			raise ValueError("There must be exactly the same number of input zs as the number of triangulated points.")
		grid=np.empty((nrows,ncols),dtype=np.float32)
		if return_triangles:
			t_grid=np.zeros((nrows,ncols),dtype=np.float32)
			p_t_grid=t_grid.ctypes.data_as(LP_CFLOAT)
		else:
			p_t_grid=None
		lib.make_grid(self.points.ctypes.data_as(LP_CDOUBLE),z_base.ctypes.data_as(LP_CDOUBLE),self.vertices,grid.ctypes.data_as(LP_CFLOAT),p_t_grid,nd_val,ncols,nrows,cx,cy,xl,yu,self.index)
		if return_triangles:
			return grid,t_grid
		else:
			return grid
	def make_grid_low(self,z_base,ncols,nrows,xl,cx,yu,cy,nd_val=-999,cut_off=1.5):
		#void make_grid(double *base_pts,double *base_z, int *tri, double *grid, double nd_val, int ncols, int nrows, double cx, double cy, double xl, double yu, spatial_index *ind)
		if z_base.shape[0]!=self.points.shape[0]:
			raise ValueError("There must be exactly the same number of input zs as the number of triangulated points.")
		grid=np.empty((nrows,ncols),dtype=np.float32)
		lib.make_grid_low(self.points.ctypes.data_as(LP_CDOUBLE),z_base.ctypes.data_as(LP_CDOUBLE),self.vertices,grid.ctypes.data_as(LP_CFLOAT),nd_val,ncols,nrows,cx,cy,xl,yu,cut_off,self.index)
		return grid
		
	def get_triangles(self,indices): 
		"""Copy allocated triangles to numpy (n,3) int32 array. Invalid indices give (-1,-1,-1) rows."""
		self.validate_points(indices,1,np.int32)
		out=np.empty((indices.shape[0],3),dtype=np.int32)
		lib.get_triangles(self.vertices,indices.ctypes.data_as(LP_CINT),out.ctypes.data_as(LP_CINT),indices.shape[0],self.ntrig)
		return out
	def get_triangle_centers(self):
		out=np.empty((self.ntrig,2),dtype=np.float64)
		lib.get_triangle_centers(self.points.ctypes.data_as(LP_CDOUBLE),self.vertices,out.ctypes.data_as(LP_CDOUBLE),self.ntrig)
		return out
	def rebuild_index(self,cs):
		"""Rebuild index with another cell size"""
		lib.free_index(self.index)
		self.index=lib.build_index(self.points.ctypes.data_as(LP_CDOUBLE),self.vertices,cs,self.points.shape[0],self.ntrig)
	def optimize_index(self):
		"""Only shrinks index slightly in memory. Should also sort index after areas of intersections between cells and triangles..."""
		lib.optimize_index(self.index)
	def inspect_index(self):
		"""Return info as text"""
		info=ctypes.create_string_buffer(1024)
		lib.inspect_index(self.index,info,1024)
		return info.value
	def find_triangles(self,xy,mask=None):
		"""Finds triangle indices of input points. Returns -1 if no triangles is found."""
		self.validate_points(xy)
		out=np.empty((xy.shape[0],),dtype=np.int32)
		if mask is not None:
			if mask.shape[0]!=self.ntrig:
				raise ValueError("Validity mask size differs from number of triangles")
			self.validate_points(mask,ndim=1,dtype=np.bool)
			pmask=mask.ctypes.data_as(LP_CCHAR)
		else:
			pmask=None
		lib.find_triangle(xy.ctypes.data_as(LP_CDOUBLE),out.ctypes.data_as(LP_CINT),self.points.ctypes.data_as(LP_CDOUBLE),self.vertices,self.index,pmask,xy.shape[0])
		return out
	




def main(args):
	#Test that things work. Call with number_of_vertices number_of_points_to_interpolate
	n1=int(args[1])
	n2=int(args[2])
	points=np.random.rand(n1,2)*1000.0
	z=np.random.rand(n1)*100
	xmin,ymin=points.min(axis=0)
	xmax,ymax=points.max(axis=0)
	print "Span of 'pointcloud':",xmin,ymin,xmax,ymax
	dx=(xmax-xmin)
	dy=(ymax-ymin)
	cx,cy=points.mean(axis=0)
	xy=np.random.rand(n2,2)*[dx,dy]*0.3+[cx,cy]
	t1=time.clock()
	tri=Triangulation(points,-1)
	t2=time.clock()
	t3=t2-t1
	print("Building triangulation and index of %d points: %.4f s" %(n1,t3))
	print tri.inspect_index()
	t1=time.clock()
	tri.optimize_index()
	t2=time.clock()
	t3=t2-t1
	print("\n%s\nOptimizing index: %.4fs" %("*"*50,t3))
	print tri.inspect_index()
	t1=time.clock()
	T=tri.find_triangles(xy)
	t2=time.clock()
	t3=t2-t1
	print("Finding %d simplices: %.4f s, pr. 1e6: %.4f s" %(n2,t3, t3/n2*1e6))
	print T.min(),T.max()
	t1=time.clock()
	zi=tri.interpolate(z,points)
	t2=time.clock()
	t3=t2-t1
	print("Interpolation test of vertices:  %.4f s, pr. 1e6: %.4f s"%(t3, t3/n1*1e6))
	D=np.fabs(z-zi)
	print "Diff: ",D.max(),D.min(),D.mean()
	print "Span: ",zi.max(),zi.min()
	
	

if __name__=="__main__":
	main(sys.argv)
	
