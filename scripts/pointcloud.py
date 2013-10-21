############################
##  Pointcloud utility class - wraps many useful methods
##
############################

import sys,os 
import numpy as np
from triangle import triangle
from slash import slash

#read a las file and return a pointcloud
def las2pointcloud(path):
	plas=slash.LasFile(path)
	r=plas.read_records()
	plas.close()
	return Pointcloud(r["xy"],r["z"],r["c"],r["pid"])  #or **r.....
	

class Pointcloud(object):
	def __init__(self,xy,z=None,c=None,pid=None):
		self.xy=xy
		self.z=z
		self.c=c
		self.pid=pid
		self.triangulation=None
		self.bbox=None  #[x1,y1,x2,y2,z1,z2]
	def get_bounds(self):
		if self.bbox is None:
			self.bbox=np.ones((6,),dtype=np.float64)*-999
			self.bbox[0:2]=np.min(self.xy,axis=0)
			self.bbox[2:4]=np.max(self.xy,axis=0)
			if self.z is not None:
				self.bbox[4]=np.min(self.z)
				self.bbox[5]=np.max(self.z)
		return self.bbox
	def get_size(self):
		return self.xy.shape[0]
	def get_classes(self):
		if self.c is not None:
			return np.unique(self.c)
		else:
			return []
	def cut_to_box(self,xmin,ymin,xmax,ymax):
		I=np.logical_and((self.xy>=(xmin,ymin)),(self.xy<=(xmax,ymax))).all(axis=1)
		lxy=self.xy[I]
		pc=pointcloud(lxy)
		if self.z is not None:
			pc.z=self.z[I]
		if self.c is not None:
			pc.c=self.c[I]
		if self.pid is not None:
			pc.pid=self.pid[I]
		return pc
	def cut_to_class(self,c):
		if self.c is not None:
			I=(self.c==c)
			lxy=self.xy[I]
			pc=pointcloud(lxy,c=self.c[I])
			if self.z is not None:
				pc.z=self.z[I]
			if self.pid is not None:
				pc.pid=self.pid[I]
			return pc
		return None
	def cut_to_z_interval(self,zmin,zmax):
		if self.z is not None:
		#Hvad betyder .all(axis=1)
			I=np.locical_and((self.z>=zmin),(self.z<=zmax))
			lxy=self.xy[I]
			pc=pointcloud(lxy)
			pc.z=self.z[I]
			if self.c is not None:
				pc.c=self.c[I]
			if self.pid is not None:
				pc.pid=self.pid[I]
		else:
			return None
	def triangulate(self):
		self.triangulation=triangle.Triangulation(self.xy)
		
	def get_grid(self,ncols=None,nrows=None,x1=None,x2=None,y1=None,y2=None,cx=None,cy=None,nd_val=-999):
		#xl = left 'corner' of "pixel", not center.
		#yu= upper 'corner', not center.
		#returns grid and gdal style georeference...
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
		if self.z is None:
			raise Exception("Z field not set.")
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
		return self.triangulation.make_grid(self.z,ncols,nrows,x1,cx,y2,cy,nd_val),geo_ref
	
	def find_appropriate_triangles(self,xy_in,tol_xy=1.5,tol_z=0.2):
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
		if self.z is None:
			raise Exception("Z field not set.")
		return self.triangulation.find_appropriate_triangles(self.z,xy_in,tol_xy,tol_z)
	
	def interpolate(self,xy_in,nd_val=-999):
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
		if self.z is None:
			raise Exception("Z field not set.")
		return self.triangulation.interpolate(self.z,xy_in,nd_val)
	
	def controlled_interpolation(self,xy_in,tol_xy=1.5,tol_z=0.2,nd_val=-999):
		#TODO - make a c method which controls bbox in interpolation
		if self.triangulation is None:
			raise Exception("Create a triangulation first...")
		if self.z is None:
			raise Exception("Z field not set.")
		I=self.triangulation.find_appropriate_triangles(self.z,xy_in,tol_xy,tol_z)
		M=(I>=0)
		zout=self.triangulation.interpolate(self.z,xy_in,nd_val)
		zout[M]=nd_val
		return zout
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
	