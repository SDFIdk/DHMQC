###############################################
## PcPlot plugin for visualising pointclouds with matplotlib    ##
## simlk, june 2014.
###############################################
from PyQt4 import QtCore, QtGui 
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from qgis.core import *
from Ui_PcPlot import Ui_Dialog
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import glob
from thatsDEM import pointcloud, array_geometry
from osgeo import ogr
import os,sys,time

#see dhmqc_constants
c_to_color={1:"magenta",2:"brown",3:"orange",4:"cyan",5:"green",6:"red",7:"pink",9:"blue",17:"gray"}
c_to_name={0:"unused",1:"surface",2:"terrain",3:"low_veg",4:"med_veg",5:"high_veg",6:"building",7:"outliers",8:"mod_key",9:"water",
10:"ignored",17:"bridge",32:"man_excl"}
def plot2d(pc,poly,title=None):
	plt.figure()
	if title is not None:
		plt.title(title)
	cs=pc.get_classes()
	for c in cs:
		pcc=pc.cut_to_class(c)
		if c in c_to_color:
			col=c_to_color[c]
		else:
			col="black"
		if c in c_to_name:
			label=c_to_name[c]
		else:
			label="class {0:d}".format(c)
		plt.plot(pcc.xy[:,0],pcc.xy[:,1],".",label=label,color=col)
	plt.plot(poly[0][:,0],poly[0][:,1],linewidth=2.5,color="black")
	plt.axis("equal")
	plt.legend()
	plt.show()

def plot3d(pc,title=None):
	fig = plt.figure()
	ax = Axes3D(fig)
	if title is not None:
		plt.title(title)
	cs=pc.get_classes()
	for c in cs:
		pcc=pc.cut_to_class(c)
		if c in c_to_color:
			col=c_to_color[c]
		else:
			col="black"
		ax.scatter(pcc.xy[:,0], pcc.xy[:,1], pcc.z,s=2.8,c=col)
	plt.show()
	
class PcPlot_dialog(QtGui.QDialog,Ui_Dialog):
	def __init__(self,iface): 
		QtGui.QDialog.__init__(self) 
		self.setupUi(self)
		self.iface = iface
		self.dir = "/"
		self.lasfiles=[]
		self.las_path=None
		#data to check if we should reload pointcloud...
		self.pc_in_poly=None
		self.poly_array=None
	@pyqtSignature('') #prevents actions being handled twice
	def on_bt_browse_clicked(self):
		f_name = str(QFileDialog.getExistingDirectory(self, "Select a directory containing las files:",self.dir))
		if len(f_name)>0:
			self.txt_las_path.setText(f_name)
			self.dir=unicode(f_name)
	@pyqtSignature('')
	def on_bt_refresh_clicked(self):
		self.cb_vectorlayers.clear()
		mc = self.iface.mapCanvas()
		nLayers = mc.layerCount()
		layers=[]
		for l in range(nLayers):
			layer = mc.layer(l)
			if layer.type()== layer.VectorLayer and layer.geometryType()==QGis.Polygon:
				layers.append(layer.name())
		self.cb_vectorlayers.addItems(layers)
	@pyqtSignature('')
	def on_bt_z_interval_clicked(self):
		self.txt_log.clear()
		pc,arr=self.getPointcloudAndPoly()
		if pc is None:
			return
		if pc.get_size()==0:
			self.log("Sorry no points in polygon!","orange")
			return
		z1=pc.z.min()
		z2=pc.z.max()
		self.log("z_min: {0:.2f} z_max: {1:.2f}".format(z1,z2),"blue")
		self.spb_min.setValue(z1)
		self.spb_max.setValue(z2)
		
	@pyqtSignature('')
	def on_bt_plot3d_clicked(self):
		self.plotNow(dim=3)
	@pyqtSignature('')
	def on_bt_plot2d_clicked(self):
		#get input#
		self.plotNow(dim=2)
	def polysEqual(self,poly1,poly2):
		#check if two of our custom polygon coord lists are equal
		if len(poly1)!=len(poly2):
			return False
		for i in range(len(poly1)):
			if poly1[i].shape!=poly2[i].shape:
				return False
			if not (poly1[i]==poly2[i]).all():
				return False
		return True
	def loadPointcloud(self,arr):
		#load a pointcloud from a 2d-numpy array... (xy-verts)
		x1,y1=arr[0].min(axis=0)
		x2,y2=arr[0].max(axis=0)
		files_to_load=[]
		for x,y in ((x1,y1),(x1,y2),(x2,y1),(x2,y2)):
			kmname=self.coord2KmName(x,y)
			if not kmname in files_to_load:
				files_to_load.append(kmname)
		found=[]
		for name in files_to_load:
			for lasname in self.lasfiles:
				bname=os.path.basename(lasname)
				if name in bname:
					found.append(lasname)
		self.log("Found {0:d} las file(s) that might intersect polygon...".format(len(found)))
		if len(found)==0:
			self.log("Didn't find any las files :-(","red")
			return None,None
		xy=np.empty((0,2),dtype=np.float64)
		z=np.empty((0,),dtype=np.float64)
		c=np.empty((0,),dtype=np.int32)
		for las_name in found:
			try:
				pc=pointcloud.fromLAS(las_name)
			except Exception,e:
				self.log(str(e))
				continue
			pcp=pc.cut_to_polygon(arr)
			if xy.shape[0]>1e6:
				self.log("Already too many points to plot!","orange")
				continue
			xy=np.vstack((xy,pcp.xy))
			z=np.append(z,pcp.z)
			c=np.append(c,pcp.c)
		if xy.shape[0]==0:
			self.log("Hmmm - something wrong. No points loaded...","red")
			return None,None
		return pointcloud.Pointcloud(xy,z,c)
	def getPointcloudAndPoly(self):
		#Method to call whenever we need to do something with the pointcloud - checks if we should reload, etc.
		is_new=False
		las_path=unicode(self.txt_las_path.text())
		if len(las_path)==0:
			self.message("Please select a las directory first!")
			return None,None
		#check if we should update las files...
		if las_path !=self.las_path:
			is_new=True
			self.dir=las_path
			self.las_path=las_path
			n_files=self.updateLasFiles(las_path)
			self.log("{0:d} las files in {1:s}".format(n_files,las_path),"blue")
			if n_files==0:
				self.log("Please select another directory!","red")
				return None,None
		vlayer_name=self.cb_vectorlayers.currentText() #should alwyas be '' if no selection
		if vlayer_name is None or len(vlayer_name)==0:
			self.log("No polygon layers loaded!","red")
			return None,None
		layers=QgsMapLayerRegistry.instance().mapLayersByName(vlayer_name)
		if len(layers)==0:
			self.log("No layer named "+vlayer_name,"red")
			return None,None
		layer=layers[0]
		n_selected=layer.selectedFeatureCount()
		if n_selected==0:
			self.log("Select at lest one polygon feature from "+vlayer_name,"red")
			return None,None
		if n_selected>1:
			self.log("More than one feature selected - using the first one...","orange")
		feat=layer.selectedFeatures()[0]
		geom=feat.geometry()
		ogr_geom=ogr.CreateGeometryFromWkt(str(geom.exportToWkt()))
		arr=array_geometry.ogrpoly2array(ogr_geom)
		if (self.pc_in_poly is None) or (self.poly_array is None) or (not self.polysEqual(arr,self.poly_array)):
			#polygon has changed! or pc not loaded...
			self.poly_array=arr
			self.log("Loading pointcloud...","blue")
			self.pc_in_poly=self.loadPointcloud(self.poly_array)
		return self.pc_in_poly,self.poly_array
			
	def updateLasFiles(self,path):
		path=path.replace("*.las","")
		self.lasfiles=glob.glob(os.path.join(path,"*.las"))
		return len(self.lasfiles)
	def coord2KmName(self,x,y):
		E="{0:d}".format(int(x/1e3))
		N="{0:d}".format(int(y/1e3))
		return N+"_"+E
	def plotNow(self,dim=2):
		self.txt_log.clear()
		pc,arr=self.getPointcloudAndPoly()
		if pc is None:
			return
		if self.chb_restrict.isChecked():
			z1=float(self.spb_min.value())
			z2=float(self.spb_max.value())
			if z1>=z2:
				self.log("zmin cannot be larger that zmax!","red")
				return
			pc=pc.cut_to_z_interval(z1,z2)
			title="Cut to z-interval ({0:0.2f},{1:.2f})".format(z1,z2)
		else:
			title=None
		if pc.get_size()==0:
			self.log("Sorry no points in polygon!","orange")
			return
		self.log("Plotting in dimension: "+str(dim),"blue")
		if dim==2:
			plot2d(pc,arr,title)
		else:
			if pc.get_size()>2*1e5:
				self.log("Oh no - too many points for that!","orange")
				return
			plot3d(pc,title)

	def message(self,text,title="Error"):
		QMessageBox.warning(self,title,text)
	def log(self,text,color="black"):
		self.txt_log.setTextColor(QColor(color))
		self.txt_log.append(text)
		

	