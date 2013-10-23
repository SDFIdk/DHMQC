############################
##  Pointcloud utility class - wraps many useful methods
##
############################

import sys,os 
import numpy as np
import triangle, slash
#should perhaps not be done for the user behind the curtains?? Might copy data!
from array_factory import point_factory, z_factory, int_array_factory 
import array_geometry
#Should perhaps be moved to method in order to speed up import...
from grid import Grid




#read a las file and return a pointcloud
def fromLAS(path):
	plas=slash.LasFile(path)
	r=plas.read_records()
	plas.close()
	return Pointcloud(r["xy"],r["z"],r["c"],r["pid"])  #or **r would look more fancy








class Pointcloud(object):
	"""
	Pointcloud class constructed from a xy and a z array. Optionally also classification and point source id integer arrays
	"""
	def __init__(self,xy,z,c=None,pid=None):
		self.xy=point_factory(xy)
		self.z=z_factory(z)
		if z.shape[0]!=xy.shape[0]:
			raise ValueError("z must have length equal to number of xy-points")
		self.c=int_array_factory(c) #todo: factory functions for integer arrays...
		self.pid=int_array_factory(pid)
		self.triangulation=None
		self.bbox=None  #[x1,y1,x2,y2]
	def might_overlap(self,other):
		return self.might_intersect_box(other.get_bounds())
	def might_intersect_box(self,box): #box=(x1,y1,x2,y2)
		b1=self.get_bounds()
		xhit=box[0]<=b1[0]<=box[2] or  b1[0]<=box[0]<=b1[2]
		yhit=box[1]<=b1[1]<=box[3] or  b1[1]<=box[1]<=b2[3]
		return xhit and yhit
	def get_bounds(self):
		if self.bbox is None:
			if self.xy.shape[0]>0:
				self.bbox=np.ones((4,),dtype=np.float64)
				self.bbox[0:2]=np.min(self.xy,axis=0)
				self.bbox[2:4]=np.max(self.xy,axis=0)
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
	def get_pids(self):
		if self.pid is not None:
			return np.unique(self.pid)
		else:
			return []
	def cut(self,mask):
		pc=Pointcloud(self.xy[mask],self.z[mask])
		if self.c is not None:
			pc.c=self.c[mask]
		if self.pid is not None:
			pc.pid=self.pid[mask]
		return pc
	def cut_to_polygon(self,vertices):
		I=array_geometry.points_in_polygon(self.xy,vertics)
		return self.cut(I)
	def cut_to_line_buffer(self,vertices,dist):
		I=array_geomety.points_in_buffer(self.xy,vertices,dist)
		return self.cut(I)
	def cut_to_box(self,xmin,ymin,xmax,ymax):
		I=np.logical_and((self.xy>=(xmin,ymin)),(self.xy<=(xmax,ymax))).all(axis=1)
		return self.cut(I)
	def cut_to_class(self,c=None):
		if self.c is not None:
			if c is None:
				return self
			I=(self.c==c)
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
	def get_grid(self,ncols=None,nrows=None,x1=None,x2=None,y1=None,y2=None,cx=None,cy=None,nd_val=-999,crop=0):
		#xl = left 'corner' of "pixel", not center.
		#yu= upper 'corner', not center.
		#returns grid and gdal style georeference...
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
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
			raise ValueError("Unable to computer grid extent from input data")
		if nrows is None and cy is None:
			raise ValueError("Unable to computer grid extent from input data")
		if ncols is None:
			ncols=int((x2-x1)/cx)+1
		else:
			cx=(x2-x1)/float(ncols)
		if nrows is None:
			nrows=int((y2-y1)/cy)+1
		else:
			cy=(y2-y1)/float(nrows)
		#geo ref gdal style...
		geo_ref=[x1,cx,0,y2,0,-cy]
		return Grid(self.triangulation.make_grid(self.z,ncols,nrows,x1,cx,y2,cy,nd_val),geo_ref,nd_val)
	
	def find_appropriate_triangles(self,xy_in,tol_xy=1.5,tol_z=0.2):
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
		xy_in=point_factory(xy_in)
		return self.triangulation.find_appropriate_triangles(self.z,xy_in,tol_xy,tol_z)
	
	def interpolate(self,xy_in,nd_val=-999):
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
		xy_in=point_factory(xy_in)
		return self.triangulation.interpolate(self.z,xy_in,nd_val)
	
	def controlled_interpolation(self,xy_in,tol_xy=1.5,tol_z=0.2,nd_val=-999):
		#TODO - make a c method which controls bbox in interpolation
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
		xy_in=point_factory(xy_in)
		I=self.triangulation.find_appropriate_triangles(self.z,xy_in,tol_xy,tol_z)
		M=(I>=0)
		zout=self.triangulation.interpolate(self.z,xy_in,nd_val)
		zout[M]=nd_val
		return zout
	def warp(self,sys_in,sys_out):
		pass #TODO - use TrLib
	#dump all data to a npz-file...??#
	def dump(self,path):
		print("TODO")
	
	
		
		
