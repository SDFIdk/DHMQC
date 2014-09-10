############################
##  Pointcloud utility class - wraps many useful methods
##
############################

import sys,os 
import numpy as np
from osgeo import gdal
import triangle, slash
#should perhaps not be done for the user behind the curtains?? Might copy data!
from array_factory import point_factory, z_factory, int_array_factory 
import array_geometry
import vector_io
#Should perhaps be moved to method in order to speed up import...
import grid
from math import ceil




#read a las file and return a pointcloud - spatial selection by xy_box (x1,y1,x2,y2) and / or z_box (z1,z2)
def fromLAS(path,include_return_number=False,xy_box=None, z_box=None):
	plas=slash.LasFile(path)
	r=plas.read_records(return_ret_number=include_return_number,xy_box=xy_box,z_box=z_box)
	plas.close()
	return Pointcloud(r["xy"],r["z"],r["c"],r["pid"],r["rn"])  #or **r would look more fancy

#make a (geometric) pointcloud from a grid
def fromGrid(path):
	ds=gdal.Open(path)
	geo_ref=ds.GetGeoTransform()
	nd_val=ds.GetRasterBand(1).GetNoDataValue()
	z=ds.ReadAsArray().astype(np.float64)
	ds=None
	x=geo_ref[0]+geo_ref[1]*0.5+np.arange(0,z.shape[1])*geo_ref[1]
	y=geo_ref[3]+geo_ref[5]*0.5+np.arange(0,z.shape[0])*geo_ref[5]
	z=z.flatten()
	x,y=np.meshgrid(x,y)
	xy=np.column_stack((x.flatten(),y.flatten()))
	M=(z!=nd_val)
	if not M.all():
		xy=xy[M]
		z=z[M]
	return Pointcloud(xy,z)

#make a (geometric) pointcloud from a (xyz) text file 
def fromText(path,delim=None):
	points=np.loadtxt(path,delimiter=delim)
	if points.ndim==1:
		points=points.reshape((1,3))
	return Pointcloud(points[:,:2],points[:,2])

#make a (geometric) pointcloud form an OGR readable point datasource. TODO: handle multipoint features....
def fromOGR(path):
	geoms=vector_io.get_geometries(path)
	points=array_geometry.ogrpoints2array(geoms)
	if points.ndim==1:
		points=points.reshape((1,3))
	return Pointcloud(points[:,:2],points[:,2])

class Pointcloud(object):
	"""
	Pointcloud class constructed from a xy and a z array. Optionally also classification and point source id integer arrays
	"""
	def __init__(self,xy,z,c=None,pid=None,rn=None):
		self.xy=point_factory(xy)
		self.z=z_factory(z)
		if z.shape[0]!=xy.shape[0]:
			raise ValueError("z must have length equal to number of xy-points")
		self.c=int_array_factory(c) 
		self.rn=int_array_factory(rn)
		self.pid=int_array_factory(pid)
		self.triangulation=None
		self.triangle_validity_mask=None
		self.bbox=None  #[x1,y1,x2,y2]
		self.index_header=None
		self.spatial_index=None
		#TODO: implement attributte handling nicer....
		self.pc_attrs=["xy","z","c","pid","rn"]
	
	def extend(self,other):
		#Other must have at least as many attrs as this... rather than unexpectedly deleting attrs raise an exception, or what... time will tell what the proper implementation is...
		if not isinstance(other,Pointcloud):
			raise ValueError("Other argument must be a Pointcloud")
		for a in self.pc_attrs:
			if (self.__dict__[a] is not None) and (other.__dict__[a] is None):
				raise ValueError("Other pointcloud does not have attributte "+a+" which this has...")
		#all is well and we continue - garbage collect previous deduced objects...
		self.triangulation=None
		self.index_header=None
		self.spatial_index=None
		self.bbox=None
		self.triangle_validity_mask=None
		for a in self.pc_attrs:
			if self.__dict__[a] is not None:
				self.__dict__[a]=np.require(np.concatenate((self.__dict__[a],other.__dict__[a])), requirements=['A', 'O', 'C'])
			
	
	def might_overlap(self,other):
		return self.might_intersect_box(other.get_bounds())
	
	def might_intersect_box(self,box): #box=(x1,y1,x2,y2)
		if self.xy.shape[0]==0 or box is None:
			return False
		b1=self.get_bounds()
		xhit=box[0]<=b1[0]<=box[2] or  b1[0]<=box[0]<=b1[2]
		yhit=box[1]<=b1[1]<=box[3] or  b1[1]<=box[1]<=b1[3]
		return xhit and yhit
	
	def get_bounds(self):
		if self.bbox is None:
			if self.xy.shape[0]>0:
				self.bbox=array_geometry.get_bounds(self.xy)
			else:
				return None
		return self.bbox
	
	def get_z_bounds(self):
		if self.z.size>0:
			return np.min(self.z),np.max(self.z)
		else:
			return None
	def get_size(self):
		return self.xy.shape[0]
	def get_classes(self):
		if self.c is not None:
			return np.unique(self.c)
		else:
			return []
	def get_strips(self):
		return self.get_pids()
	def get_pids(self):
		if self.pid is not None:
			return np.unique(self.pid)
		else:
			return []
	def get_return_numbers(self):
		if self.rn is not None:
			return np.unique(self.rn)
		else:
			return []
	def cut(self,mask):
		if self.xy.size==0: #just return something empty to protect chained calls...
			return self
		pc=Pointcloud(self.xy[mask],self.z[mask])
		if self.c is not None:
			pc.c=self.c[mask]
		if self.pid is not None:
			pc.pid=self.pid[mask]
		if self.rn is not None:
			pc.rn=self.rn[mask]
		return pc
	def cut_to_polygon(self,rings):
		I=array_geometry.points_in_polygon(self.xy,rings)
		return self.cut(I)
	def cut_to_line_buffer(self,vertices,dist):
		I=array_geometry.points_in_buffer(self.xy,vertices,dist)
		return self.cut(I)
	def cut_to_box(self,xmin,ymin,xmax,ymax):
		I=np.logical_and((self.xy>=(xmin,ymin)),(self.xy<=(xmax,ymax))).all(axis=1)
		return self.cut(I)
	def cut_to_class(self,c,exclude=False):
		#will now accept a list or another iterable...
		if self.c is not None:
			try:
				cs=iter(c)
			except:
				cs=(c,)
			if exclude:
				I=np.ones((self.c.shape[0],),dtype=np.bool)
			else:
				I=np.zeros((self.c.shape[0],),dtype=np.bool)
			#TODO: use inplace operations to speed up...
			for this_c in cs:
				if exclude:
					I&=(self.c!=this_c)
				else:
					I|=(self.c==this_c)
			return self.cut(I)
		return None
	def cut_to_return_number(self,rn):
		if self.rn is not None:
			I=(self.rn==rn)
			return self.cut(I)
		return None
	def cut_to_z_interval(self,zmin,zmax):
		I=np.logical_and((self.z>=zmin),(self.z<=zmax))
		return self.cut(I) 
	def cut_to_strip(self,id):
		if self.pid is not None:
			I=(self.pid==id)
			return self.cut(I)
		else:
			return None
	def triangulate(self):
		if self.triangulation is None:
			if self.xy.shape[0]>2:
				self.triangulation=triangle.Triangulation(self.xy)
			else:
				raise ValueError("Less than 3 points - unable to triangulate.")
	def set_validity_mask(self,mask):
		if self.triangulation is None:
			raise Exception("Triangulation not created yet!")
		if mask.shape[0]!=self.triangulation.ntrig:
			raise Exception("Invalid size of triangle validity mask.")
		self.triangle_validity_mask=mask
	def clear_validity_mask(self):
		self.triangle_validity_mask=None
	def calculate_validity_mask(self,max_angle=45,tol_xy=2,tol_z=1):
		tanv2=np.tan(max_angle*np.pi/180.0)**2
		geom=self.get_triangle_geometry()
		self.triangle_validity_mask=(geom<(tanv2,tol_xy,tol_z)).all(axis=1)
	def get_validity_mask(self):
		return self.triangle_validity_mask
	def get_grid(self,ncols=None,nrows=None,x1=None,x2=None,y1=None,y2=None,cx=None,cy=None,nd_val=-999,crop=0,method="triangulation"):
		#xl = left 'corner' of "pixel", not center.
		#yu= upper 'corner', not center.
		#returns grid and gdal style georeference...
		
		#TODO: fix up logic below...
		if x1 is None:
			bbox=self.get_bounds()
			x1=bbox[0]+crop
		if x2 is None:
			bbox=self.get_bounds()
			x2=bbox[2]-crop
		if y1 is None:
			bbox=self.get_bounds()
			y1=bbox[1]+crop
		if y2 is None:
			bbox=self.get_bounds()
			y2=bbox[3]-crop
		if ncols is None and cx is None:
			raise ValueError("Unable to compute grid extent from input data")
		if nrows is None and cy is None:
			raise ValueError("Unable to compute grid extent from input data")
		if ncols is None:
			ncols=int(ceil((x2-x1)/cx))
		else:
			cx=(x2-x1)/float(ncols)
		if nrows is None:
			nrows=int(ceil((y2-y1)/cy))
		else:
			cy=(y2-y1)/float(nrows)
		#geo ref gdal style...
		geo_ref=[x1,cx,0,y2,0,-cy]
		if method=="triangulation":
			if self.triangulation is None:
				raise Exception("Create a triangulation first...")
			return grid.Grid(self.triangulation.make_grid(self.z,ncols,nrows,x1,cx,y2,cy,nd_val),geo_ref,nd_val)
		elif method=="density": #density grid
			arr_coords=((self.xy-(geo_ref[0],geo_ref[3]))/(geo_ref[1],geo_ref[5])).astype(np.int32)
			M=np.logical_and(arr_coords[:,0]>=0, arr_coords[:,0]<ncols)
			M&=np.logical_and(arr_coords[:,1]>=0,arr_coords[:,1]<nrows)
			arr_coords=arr_coords[M]
			# Wow - this gridding is sooo simple! and fast!
			#create flattened index
			B=arr_coords[:,1]*ncols+arr_coords[:,0]
			bins=np.arange(0,ncols*nrows+1)
			h,b=np.histogram(B,bins)
			h=h.reshape((nrows,ncols))
			return grid.Grid(h,geo_ref,0) #zero always nodata value here...
		elif "class" in method:
			#define method which takes the most frequent value in a cell... could be only mean...
			most_frequent=lambda x:np.argmax(np.bincount(x))
			g=grid.make_grid(self.xy,self.c,ncols,nrows,geo_ref,255,method=most_frequent,dtype=np.int32)
			g.grid=g.grid.astype(np.uint8)
			return g
		else:
			return None
	def find_triangles(self,xy_in,mask=None):
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
		xy_in=point_factory(xy_in)
		#-2 indices signals outside triangulation, -1 signals invalid, else valid
		return self.triangulation.find_triangles(xy_in,mask)
		
	def find_appropriate_triangles(self,xy_in,mask=None):
		if mask is None:
			mask=self.triangle_validity_mask
		if mask is None:
			raise Exception("This method needs a triangle validity mask.")
		return self.find_triangles(xy_in,mask)
	
	def get_points_in_triangulation(self,xy_in):
		I=find_triangles(xy_in)
		return xy_in[I>=0]
		
	def get_points_in_valid_triangles(self,xy_in,mask=None):
		I=find_appropriate_triangles(self,xy_in,mask)
		return xy_in[I>=0]
	
	def get_boundary_vertices(self,M_t,M_p): #hmmm - find the vertices which are marked by M_p and in triangles marked by M_t
		M_out=array_geometry.get_boundary_vertices(M_t,M_p,self.triangulation.vertices)
		return M_out
		
	def interpolate(self,xy_in,nd_val=-999,mask=None):
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
		xy_in=point_factory(xy_in)
		return self.triangulation.interpolate(self.z,xy_in,nd_val,mask)
	#Interpolates points in valid triangles
	def controlled_interpolation(self,xy_in,mask=None,nd_val=-999):
		if mask is None:
			mask=self.triangle_validity_mask
		if mask is None:
			raise Exception("This method needs a triangle validity mask.")
		return self.interpolate(xy_in,nd_val,mask)
		
	def get_triangle_geometry(self):
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
		return array_geometry.get_triangle_geometry(self.xy,self.z,self.triangulation.vertices,self.triangulation.ntrig)
	def warp(self,sys_in,sys_out):
		pass #TODO - use TrLib
	def dump_csv(self,f,callback=None):
		#dump as a csv-file - this is gonna be slow. TODO: rewrite in z...
		f.write("x,y,z")
		has_c=False
		if self.c is not None:
			f.write(",c")
			has_c=True
		has_id=False
		if self.pid is not None:
			f.write(",strip")
			has_id=True
		f.write("\n")
		n=self.get_size()
		for i in xrange(n):
			f.write("{0:.2f},{1:.2f},{2:.2f}".format(self.xy[i,0],self.xy[i,1],self.z[i]))
			if has_c:
				f.write(",{0:d}".format(self.c[i]))
			if has_id:
				f.write(",{0:d}".format(self.pid[i]))
			f.write("\n")
			if callback is not None and i>0 and i%1e4==0:
				callback(i)
	def sort_spatially(self,cs):
		if self.get_size()==0:
			raise Exception("No way to sort an empty pointcloud.")
		x1,y1,x2,y2=self.get_bounds()
		ncols=int((x2-x1)/cs)+1
		nrows=int((y2-y1)/cs)+1
		arr_coords=((self.xy-(x1,y2))/(cs,-cs)).astype(np.int32)
		B=arr_coords[:,1]*ncols+arr_coords[:,0]
		I=np.argsort(B)
		B=B[I]
		self.spatial_index=np.ones((ncols*nrows,),dtype=np.int32)*-1
		res=array_geometry.lib.fill_spatial_index(B,self.spatial_index,B.shape[0],self.spatial_index.shape[0])
		if  res!=0:
			raise Exception("Size of spatial index array too small! Programming error!")
		self.xy=self.xy[I]
		self.z=self.z[I]
		if self.c is not None:
			self.c=self.c[I]
		if self.pid is not None:
			self.pid=self.pid[I]
		if self.rn is not None:
			self.rn=self.rn[I]
		#remember to save cellsize, ncols and nrows... TODO: in an object...
		self.index_header=np.asarray((ncols,nrows,x1,y2,cs),dtype=np.float64)
		return self
	def min_filter(self, filter_rad):
		if self.spatial_index is None:
			raise Exception("Build a spatial index first!")
		z_out=np.empty_like(self.z)
		array_geometry.lib.pc_min_filter(self.xy,self.z,z_out,filter_rad,self.spatial_index,self.index_header,self.xy.shape[0])
		return z_out
	def max_filter(self):
		pass
	def median_filter(self):
		pass
	def spike_filter(self, filter_rad,tanv2,zlim=0.2):
		if self.spatial_index is None:
			raise Exception("Build a spatial index first!")
		if (tanv2<0 or zlim<0):
			raise ValueError("Spike parameters must be positive!")
		z_out=np.empty_like(self.z)
		array_geometry.lib.pc_spike_filter(self.xy,self.z,z_out,filter_rad,tanv2,zlim,self.spatial_index,self.index_header,self.xy.shape[0])
		return z_out
		
	
	
	
		
		
