######################################
##  Grid class  - just a numpy array and some metadata + some usefull methods             
####################################
import numpy as np
import os
try:
	from osgeo import gdal
except:
	HAS_GDAL=False
else:
	HAS_GDAL=True
	
class Grid(object):
	"""
	Grid abstraction class.
	Contains a numpy array and metadata like geo reference.
	"""
	def __init__(self,arr,geo_ref,nd_val=None):
		self.grid=arr
		self.geo_ref=geo_ref
		self.nd_val=nd_val
		#and then define some useful methods...
	def save(self,fname,format="GTiff"):
		if not HAS_GDAL:
			raise Exception("This method requires GDAL python bindings!")
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
		if self.nd_val is not None:
			band.SetNoDataValue(self.nd_val)
		band.WriteArray(self.grid)
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
		#THIS is just stupid - should be done in c....
		print("Casting shadow...")
		light=np.array(light)
		light=light/(np.sqrt((light**2).sum()))
		print("Light: %s" %repr(light))
		M=(self.grid==self.nd_val)
		dx=np.zeros_like(self.grid)
		dy=np.zeros_like(self.grid)
		dx[:,0:self.grid.shape[1]-1]=self.grid[:,1:]-self.grid[:,0:self.grid.shape[1]-1]
		dy[0:self.grid.shape[0]-1]=self.grid[0:self.grid.shape[0]-1,:]-self.grid[1:,:]
		if remove_extreme and M.any(): #fast and dirty - but only works when nd-value is large compared to data!!!!!
			print("Deleting extreme slopes (probably from no-data)")
			dx[np.fabs(dx)>100]=0
			dy[np.fabs(dy)>100]=0
		if sigma>0 and False: #TODO
			dx=image.filters.gaussian_filter(dx,sigma)
			dy=image.filters.gaussian_filter(dy,sigma)
		X=np.sqrt(dx**2+dy**2+1)
		return Grid((dx*light[0]/X-dy*light[1]/X-light[2]/X)/np.sqrt(3),self.geo_ref) #cast shadow