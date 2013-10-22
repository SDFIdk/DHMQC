############################
##  Pointcloud utility class - wraps many useful methods
##
############################

import sys,os 
import numpy as np
from triangle import triangle
from slash import slash
try: #should perhaps be moved to appropriate methods to save som millisecs....
	import shapely
except:
	HAS_SHAPELY=False
else:
	HAS_SHAPELY=True
try:
	from osgeo import gdal
except:
	HAS_GDAL=False
else:
	HAS_GDAL=True


#read a las file and return a pointcloud
def fromLAS(path):
	plas=slash.LasFile(path)
	r=plas.read_records()
	plas.close()
	return Pointcloud(r["xy"],r["z"],r["c"],r["pid"])  #or **r would look more fancy

#should not make a copy if input is ok
def point_factory(xy):
	xy=np.asarray(xy)
	if xy.ndim<2: #TODO: also if shape[1]!=2
		n=xy.shape[0]
		if n%2!=0:
			raise TypeError("Input must have size n*2")
		xy=xy.reshape((int(n/2),2))
	return np.require(xy,dtype=np.float64, requirements=['A', 'O', 'C']) #aligned, own_data, c-contiguous

def z_factory(z):
	return np.require(z,dtype=np.float64, requirements=['A', 'O', 'C'])
	
def int_array_factory(I):
	if I is None:
		return None
	I=np.asarray(I)
	if I.ndim>1:
		I=np.flatten(I)
	return np.require(I,dtype=np.int32,requirements=['A','O','C'])


class Grid(object):
	def __init__(self,arr,geo_ref,nd_val=None):
		self.grid=arr
		self.geo_ref=geo_ref
		self.nd_val=nd_val
		#and then define some useful methods...
	def save(self,fname,format="GTiff"):
		if not HAS_GDAL:
			return False
		#TODO: map numpy types to gdal types better - done internally in gdal I think...
		if self.grid.dtype==np.float32:
			dtype=gdal.GDT_Float32
		elif self.grid.dtype==np.float64:
			dtype=gdal.GDT_Float64
		elif self.grid.dtype==np.int32:
			dtype=gdal.GDT_Int32
		elif self.grid.dtype==np.bool:
			dtype=gdal.GDT_Byte
		else:
			return False #TODO....
		driver=gdal.GetDriverByName(format)
		if driver is None:
			return False
		if os.path.exists(fname):
			try:
				driver.Delete(fname)
			except Exception, msg:
				print msg
			else:
				print("Overwriting %s..." %fname)	
		else:
			print("Saving %s..."%fname)
		dst_ds=driver.Create(fname,self.grid.shape[1],self.grid.shape[0],1,dtype)
		dst_ds.SetGeoTransform(self.geo_ref)
		band=dst_ds.GetRasterBand(1)
		if self.nd_value is not None:
			band.SetNoDataValue(self.nd_value)
		band.WriteArray(A)
		dst_ds=None
		return True
	def get_bounds(self):
		x1=self.geo_ref[0]
		y2=self.geo_ref[3]
		x2=x1+self.grid.shape[1]*self.geo_ref[1]
		y1=y2+self.grid.shape[0]*self.geo_ref[5]
		return (x1,y1,x2,y2)
	def correlate(self,other):
		pass #TODO
	def get_hillshade(self,light=(1,-1,-4),sigma=0,remove_extreme=False):
		pass #TODO

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
	def cut_to_line_buffer(self,vertices,dist):
		I=triangle.points_in_buffer(self.xy,vertices,dist)
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
	def get_grid(self,ncols=None,nrows=None,x1=None,x2=None,y1=None,y2=None,cx=None,cy=None,nd_val=-999):
		#xl = left 'corner' of "pixel", not center.
		#yu= upper 'corner', not center.
		#returns grid and gdal style georeference...
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
		#TODO: fix up logic below...
		if x1 is None:
			bbox=self.get_bounds()
			x1=bbox[0]
		if x2 is None:
			bbox=self.get_bounds()
			x2=bbox[2]
		if y1 is None:
			bbox=self.get_bounds()
			y1=bbox[1]
		if y2 is None:
			bbox=self.get_bounds()
			y2=bbox[3]
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
	def count_points_in_polygon(self,poly):
		if not HAS_SHAPELY:
			raise Exception("This method requires shapely")
		pc=self.cut_to_box(poly.bounds)
		mpoints=shapely.geometry.MultiPoint(pc.xy)
		intersection=mpoints.intersection(poly)	
		if intersection.is_empty:
			ncp=0
		elif isinstance(intersection,shapely.geometry.Point):
			ncp=1
		else:
			ncp=len(intersection.geoms)
		return ncp
	
	def warp(self,sys_in,sys_out):
		pass #TODO - use TrLib
	#dump all data to a npz-file...??#
	def dump(self,path):
		print("TODO")
	
	
		
		

#
#	Hvordan indlaeser vi en fil via objektet... Kunne vaere smart at definere et objekt og kalde det med obj.laeslas('filnavn')
#
#	Kunne det vaere relevant at gemme en pointcloud? altsaa have en pointcloud.write(filanvn) funktion?	
#
#
#	Der skal kunne beskaeres til en polygon			
#	def cut_to_polygon(self,poly):
#		xmin,ymin,xmax,ymax=poly.bounds
#		self.cut_to_box(xmin,ymin,xmax,ymax)
#		mpoint=shg.MultiPoint(self.xy)
	