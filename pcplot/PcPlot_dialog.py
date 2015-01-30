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
###############################################
## PcPlot plugin for visualising pointclouds with matplotlib    ##
## simlk, june 2014.
## Multithreading needs to be debugged - violates some QT rules. Logging etc should probably be event based.
## Or we couild use multiprocessing with pipes...
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
from thatsDEM import pointcloud, array_geometry,grid,dhmqc_constants
from osgeo import ogr
import os,sys,time
import threading
from math import ceil
DEBUG=False
DEF_CRS="epsg:25832"
CRS_CODE=25832
INDEX_FRMT="SQLITE"
INDEX_DSCO=["SPATIALITE=YES"]
INDEX_EXT=".sqlite"
INDEX_LAYER_NAME="las_index"
INDEX_PATH_FIELD="path"
TILE_SIZE=1e3 #1km blocks
#see dhmqc_constants
c_to_color={1:"magenta",2:"brown",3:"orange",4:"cyan",5:"green",6:"red",7:"pink",9:"blue",17:"gray"}
c_to_name={0:"unused (0)",1:"surface (1)",2:"terrain (2)",3:"low_veg (3)",
4:"med_veg (4)",5:"high_veg (5)",6:"building (6)",
7:"outliers (7)",8:"mod_key (8)",9:"water (9)",
10:"ignored (10)",17:"bridge (17)",32:"man_excl (32)"}
strip_to_color=["red","green","blue","cyan","yellow","black","orange"]  #well should'nt be anymore strips
strip_markers=["o","^"]

#TODO: add a do in background method...


	

def plot2d(pc,poly,title=None,by_strips=False, show_numbers=True):
	plt.figure()
	if title is not None and len(title)>0:
		plt.title(title)
	if by_strips:
		cs=pc.get_pids()
	else:
		cs=pc.get_classes()
	for i,c in enumerate(cs):
		if not by_strips:
			pcc=pc.cut_to_class(c)
			if c in c_to_color:
				col=c_to_color[c]
			else:
				col="black"
			if c in c_to_name:
				label=c_to_name[c]
			else:
				label="class {0:d}".format(c)
			
		else:
			pcc=pc.cut_to_strip(c)
			col=strip_to_color[i % len(strip_to_color)]
			label="strip {0:d}".format(c)
		if show_numbers:
			label+=" n={0:d}".format(pcc.get_size())
		plt.plot(pcc.xy[:,0],pcc.xy[:,1],".",label=label,color=col)
	plt.plot(poly[0][:,0],poly[0][:,1],linewidth=2.5,color="black")
	plt.axis("equal")
	plt.legend()
	plt.show()


def plot_vertical(pc,line,title=None,by_strips=False,axis_equal=True, show_numbers=True):
	plt.figure()
	if title is not None and len(title)>0:
		plt.title(title)
	if by_strips:
		cs=pc.get_pids()
	else:
		cs=pc.get_classes()
	pt=line[0]
	dir=line[-1]-line[0]
	ndir=np.sqrt((dir**2).sum())
	pc.xy-=pt
	if ndir<0.2:
		plt.title("Sorry seems to be a closed line!")
		
	else:
		dir/=ndir #normalise
		for i,c in enumerate(cs):
			if not by_strips:
				pcc=pc.cut_to_class(c)
				if c in c_to_color:
					col=c_to_color[c]
				else:
					col="black"
				if c in c_to_name:
					label=c_to_name[c]
				else:
					label="class {0:d}".format(c)
			else:
				pcc=pc.cut_to_strip(c)
				col=strip_to_color[i % len(strip_to_color)]
				label="strip {0:d}".format(c)
			if show_numbers:
				label+=" n={0:d}".format(pcc.get_size())
			x=np.dot(pcc.xy,dir)
			plt.plot(x,pcc.z,".",label=label,color=col)
		if axis_equal:
			plt.axis("equal")
		plt.legend()
	plt.show()

def plot3d(pc,title=None,by_strips=False):
	fig = plt.figure()
	ax = Axes3D(fig)
	if title is not None  and len(title)>0:
		plt.title(title)
	if by_strips:
		cs=pc.get_pids()
	else:
		cs=pc.get_classes()
	for i,c in enumerate(cs):
		if not by_strips:
			pcc=pc.cut_to_class(c)
			if c in c_to_color:
				col=c_to_color[c]
			else:
				col="black"
			
		else:
			pcc=pc.cut_to_strip(c)
			col=strip_to_color[i% len(strip_to_color)]
			
		n=pcc.get_size()
		if n>3000:
			s=2.8
		elif n>2000:
			s=4.5
		elif n>1000:
			s=6
		else:
			s=8
		ax.scatter(pcc.xy[:,0], pcc.xy[:,1], pcc.z,s=s,c=col)
	plt.axis("equal")
	plt.show()
	
class PcPlot_dialog(QtGui.QDialog,Ui_Dialog):
	def __init__(self,iface): 
		QtGui.QDialog.__init__(self) 
		self.setupUi(self)
		self.iface = iface
		self.dir = "/"
		self.lasfiles=[]
		self.las_path=None
		#Some attrs used for finishing background tasks
		self.index_layer=None
		self.index_layer_name=None
		self.grid_paths=[]
		self.grid_layer_names=[]
		self.csv_file_name=None
		#data to check if we should reload pointcloud...
		self.pc=None #buffer of last pointcloud...
		self.pc_path=None #unique identifier of the loaded pc... should be...
		self.pc_in_poly=None
		self.poly_array=None
		self.line_array=None
		self.buf_dist=None
		self.n_temp_lines=0
		self.n_temp_polys=0
		self.index_layer_ids=[]
		self.polygon_layer_ids=[]
		self.line_layer_ids=[]
		#refresh layers
		self.index_layer_ids=self.refreshPolygonLayers(self.cb_indexlayers)
		self.polygon_layer_ids=self.refreshPolygonLayers(self.cb_polygonlayers)
		self.line_layer_ids=self.refreshLineLayers(self.cb_linelayers)
		#threading stuff
		self.background_task_signal=QtCore.SIGNAL("__my_backround_task")
		QtCore.QObject.connect(self, self.background_task_signal, self.finishBackgroundTask)
		self.finish_method=None
		
	#Stuff for background processing
	def runInBackground(self,run_method,finish_method,args):
		self.log("thread_id: {0:s}".format(threading.currentThread().name),"blue")
		self.finish_method=finish_method
		self.setEnabled(False)
		thread=threading.Thread(target=run_method,args=args)
		#probably exceptions in the run method should be handled there in order to avoid a freeze...
		thread.start()
		
	
	#This is called from an emmitted event - the last execution from the run method...
	def finishBackgroundTask(self):
		self.log("thread_id: {0:s}".format(threading.currentThread().name),"blue")
		self.setEnabled(True)
		if self.finish_method is not None:
			self.finish_method()
		
	def getVectorLayer(self,id):
		layer=QgsMapLayerRegistry.instance().mapLayer(id)
		return layer
	
	
	#Three step 'rocket' to run a background task: establish data, call background method and set finish method...
	def buildIndexLayer(self):
		self.txt_log.clear()
		las_path=unicode(self.txt_las_path.text())
		if len(las_path)==0:
			self.message("Please select a las directory first!")
			return
		f_name=unicode(QFileDialog.getSaveFileName(self, "Select an output file name for las index:",self.dir,"*.shp"))
		if f_name is None or len(f_name)==0:
			return
		self.runInBackground(self.buildIndexLayerInBackground,self.finishIndexLayerTask,(las_path,f_name))
		
	def buildIndexLayerInBackground(self,las_path,f_name):
		#to be run in da background...
		try: #always escape and emit signal if something goes wrong...
			lasfiles=self.getLasFiles(las_path)
			self.log("{0:d} las files in {1:s}".format(len(lasfiles),las_path),"blue")
			if len(lasfiles)==0:
				self.log("No las files...","red")
				self.index_layer=None
				self.emit(self.background_task_signal)
			self.dir=las_path
			self.las_path=las_path
			self.dir=os.path.dirname(f_name)
			self.log("Creating index layer","blue")
			layer_name="las_index"
			ilayer=QgsVectorLayer("Polygon?crs="+DEF_CRS, layer_name,"memory")
			fields=[QgsField(INDEX_PATH_FIELD,QVariant.String)]
			#how much of this vodoo is needed??
			pr=ilayer.dataProvider()
			pr.addAttributes(fields)
			ilayer.updateFields()
			features=[]
			fields=ilayer.pendingFields()
			n_bad_names=0
			n_err=0
			for name in lasfiles:
				kmname=dhmqc_constants.get_tilename(name)
				try:
					wkt=dhmqc_constants.tilename_to_extent(kmname,return_wkt=True)
				except:
					n_bad_names+=1
					continue
				fet=QgsFeature(fields)
				fet.setGeometry(QgsGeometry.fromWkt(wkt))
				fet[INDEX_PATH_FIELD]=name
				features.append(fet)
			pr.addFeatures(features)
			ilayer.updateExtents()
			if n_bad_names>0:
				self.log("Encountered {0:d} bad 1km tile names...".format(n_bad_names),"red")
			if n_err>0:
				self.log("Encountered {0:d} errors...".format(n_err),"red")
			error = QgsVectorFileWriter.writeAsVectorFormat(ilayer, f_name, "CP1250", None, "ESRI Shapefile")
			self.index_layer=QgsVectorLayer(f_name,"las_index","ogr")
			#Now switch to main thread...
			#Emit a signal which tells what is done
		except Exception,e:
			self.log("An exception occurred {0:s}".format(str(e)),"red")
			self.index_layer=None
		self.emit(self.background_task_signal)
	def finishIndexLayerTask(self):
		self.cb_indexlayers.clear()
		if self.index_layer is not None:
			QgsMapLayerRegistry.instance().addMapLayer(self.index_layer)
			self.cb_indexlayers.addItem("las_index")
			self.index_layer_ids=[self.index_layer.id()]
	
		
	
		
	@pyqtSignature('') #prevents actions being handled twice
	def on_bt_build_index_clicked(self):
		self.buildIndexLayer()
			
	@pyqtSignature('') #prevents actions being handled twice
	def on_bt_browse_lasdir_clicked(self):
		f_name = unicode(QFileDialog.getExistingDirectory(self, "Select a directory containing las files:",self.dir))
		if len(f_name)>0:
			self.txt_las_path.setText(f_name)
			self.dir=f_name
	@pyqtSignature('') #prevents actions being handled twice
	def on_bt_browse_griddir_clicked(self):
		f_name = unicode(QFileDialog.getExistingDirectory(self, "Select a directory to save output grids in:",self.dir))
		if len(f_name)>0:
			self.txt_grid_path.setText(f_name)
			self.dir=f_name
	def getVectorLayerNames(self,ltype=None):
		loaded=QgsMapLayerRegistry.instance().mapLayers()
		layers=[]
		mc = self.iface.mapCanvas()
		nLayers = mc.layerCount()
		layers=[]
		ids=[]
		for id in loaded:
			layer = loaded[id]
			if layer.type()== layer.VectorLayer:
				do_append=True
				if ltype is not None and (ltype!=layer.geometryType()):
					do_append=False
				if do_append:
					layers.append(layer.name())
					ids.append(layer.id()) #not really documented, but should be the same as the id key used as iterator...
		return layers,ids
		
	def refreshPolygonLayers(self,box):
		box.clear()
		layers,ids=self.getVectorLayerNames(QGis.Polygon)
		box.addItems(layers)
		return ids
	def refreshLineLayers(self,box):
		box.clear()
		layers,ids=self.getVectorLayerNames(QGis.Line)
		box.addItems(layers)
		return ids
	@pyqtSignature('')
	def on_bt_refresh_index_layer_clicked(self):
		self.index_layer_ids=self.refreshPolygonLayers(self.cb_indexlayers)
	@pyqtSignature('')
	def on_bt_refresh_polygons_clicked(self):
		self.polygon_layer_ids=self.refreshPolygonLayers(self.cb_polygonlayers)
	@pyqtSignature('')
	def on_bt_refresh_lines_clicked(self):
		self.line_layer_ids=self.refreshLineLayers(self.cb_linelayers)
	@pyqtSignature('')
	def on_bt_z_interval_poly_clicked(self):
		self.update_z_interval(2)
	@pyqtSignature('')
	def on_bt_z_interval_line_clicked(self):
		self.update_z_interval(1)
	def update_z_interval(self,dim):
		self.txt_log.clear()
		data_ok,thread_started=self.getPointcloudAndVectors(dim,self.finish_update_z_interval)
		if data_ok: #data is already ok...
			self.finish_update_z_interval()
	def finish_update_z_interval(self):
		if self.pc_in_poly is None:
			return
		#self.log(str(type(pc)))
		if self.pc_in_poly.get_size()==0:
			self.log("Sorry no points in polygon/buffer!","orange")
			return
		z1=self.pc_in_poly.z.min()
		z2=self.pc_in_poly.z.max()
		self.log("z_min: {0:.2f} z_max: {1:.2f}".format(z1,z2),"blue")
		self.spb_min.setValue(z1)
		self.spb_max.setValue(z2)
	@pyqtSignature('')
	def on_bt_grid_tile_clicked(self):
		self.gridding("grid")
	@pyqtSignature('')
	def on_bt_hillshade_tile_clicked(self):
		self.gridding("hillshade")
	@pyqtSignature('')
	def on_bt_density_tile_clicked(self):
		self.gridding("density")
	@pyqtSignature('')
	def on_bt_class_tile_clicked(self):
		self.gridding("class")
	#split the gridding stuff into a 3-step process - establish data, run background method, set finish method (main thread) 
	def gridding(self,grid_type):
		self.txt_log.clear()
		index_layer_name=self.cb_indexlayers.currentText()
		index_layer_index=self.cb_indexlayers.currentIndex()
		if index_layer_name is None or len(index_layer_name)==0:
			self.message("Please select or create a las file index first")
			return
		f_name=self.txt_grid_path.text()
		if len(f_name)==0:
			self.message("Select an output directory for grids!")
			return
		if not os.path.exists(f_name):
			self.log(f_name+" does not exist!","red")
			return
		if not os.path.isdir(f_name):
			self.log(f_name+" is not a directory!","red")
			return
		cs=float(self.spb_cellsize.value())
		index_layer_id=self.index_layer_ids[index_layer_index]
		index_layer=QgsMapLayerRegistry.instance().mapLayer(index_layer_id)
		feats=index_layer.selectedFeatures()
		if len(feats)==0:
			self.log("Please select some features from the las index layer!","red")
			return
		if len(feats)>50:
			self.log("OK- thats a lot of selected features... might not be intentional...","orange")
			return
		paths=[]
		rects=[]
		for feat in feats:
			try:
				path=feat[INDEX_PATH_FIELD]
			except KeyError:
				self.log("Index layer does not have a {0:s} field.".format(INDEX_PATH_FIELD),"red")
				return
			if not os.path.exists(path):
				self.log(path+" does not exist!","red")
				return
			paths.append(path)
			rects.append(feat.geometry().boundingBox())
		self.dir=os.path.dirname(f_name)
		r_cls=None #restrict to these classes...
		cls_name="all"
		if self.chb_restrict_class.isChecked():
			try:
				r_cls=[int(x) for x in self.txt_classes.text().split(",")]
			except Exception, e:
				self.log("An exception occured: "+str(e),"red")
				self.log("Please specify a comma separated list of classes.","blue")
				return
			if len(r_cls)==0:
				self.log("Please select at least one class to restrict to!","red")
				return
			cls_name=""
			for c in r_cls:
				cls_name+=str(c)
		self.runInBackground(self.gridInBackground,self.finishGridding,(f_name,paths,rects,cs,grid_type,r_cls,cls_name))
	#the background part of the gridding...	
	def gridInBackground(self,griddir,paths,rects,cs,grid_type,r_cls=None,cls_name="all"):
		self.grid_paths=[]
		self.grid_layer_names=[]
		self.log("thread_id: {0:s}".format(threading.currentThread().name),"orange")
		cs_name="{0:.0f}".format(cs*100)
		try: #if something happens in background task - always escape and emit the signal...
			for path,rect in zip(paths,rects):
				self.log("Loading "+path,"blue")
				#check if we already have the pc in memory:
				if self.pc is not None and self.pc_path==path:
					pc=self.pc
					self.log("Loading tile from memory buffer..","blue")
				else:
					pc=pointcloud.fromLAS(path)
				#check if we should keep the last pc in memory
				if self.chb_buffer_in_mem.isChecked():
					self.pc=pc
					self.pc_path=path
				else:
					self.pc=None
					self.pc_path=None
				if r_cls is not None:
					pc=pc.cut_to_class(r_cls)
				if pc.get_size()<5:
					self.log("Too few points in pointcloud...","red")
					continue
				self.log("Bounds (from feature): {0:.2f} {1:.2f}  {2:.2f} {3:.2f}".format( rect.xMinimum(),rect.xMaximum(),rect.yMinimum(),rect.yMaximum()))
				do_save=True
				self.log("Cellsize: {0:.2f}".format(cs))
				if grid_type=="hillshade" or grid_type=="grid":
					self.log("Creating triangulation and spatial index...")
					pc.triangulate()
					self.log("Creating grid...")
					g=pc.get_grid(x1=rect.xMinimum(),x2=rect.xMaximum(),y1=rect.yMinimum(),y2=rect.yMaximum(),cx=cs,cy=cs)
					if grid_type=="hillshade":
						self.log("Creating hillshade...")
						h=g.get_hillshade()
						lname=os.path.splitext(os.path.basename(path))[0]+"_shade"
					else:
						h=g
						lname=os.path.splitext(os.path.basename(path))[0]+"_grid"
				elif grid_type=="density":
					self.log("Creating density grid...")
					h=pc.get_grid(x1=rect.xMinimum(),x2=rect.xMaximum(),y1=rect.yMinimum(),y2=rect.yMaximum(),cx=cs,cy=cs,method="density")
					lname=os.path.splitext(os.path.basename(path))[0]+"_density"
				elif grid_type=="class":
					self.log("Creating classification grid...")
					self.log("Have to loop through all points... this is gonna be slow ;-D..","orange")
					h=pc.get_grid(x1=rect.xMinimum(),x2=rect.xMaximum(),y1=rect.yMinimum(),y2=rect.yMaximum(),cx=cs,cy=cs,method="class")
					lname=os.path.splitext(os.path.basename(path))[0]+"_class"
				else:
					self.log("Not implemented...","blue")
					do_save=False
				if do_save:
					if h is None:
						self.log("Something went wrong, no grid..","orange")
					else:
						lname+="_"+cs_name
						if len(cls_name)>0:
							lname+="_"+cls_name
						outname=os.path.join(griddir,lname+".tif")
						self.log("Saving "+outname)
						h.save(outname,dco=["TILED=YES","COMPRESS=LZW"])
						self.grid_paths.append(outname)
						self.grid_layer_names.append(lname)
		except Exception,e:
			self.log("An exception occurred: {0:s}".format(str(e)),"red")
		#Now switch to main thread...
		#Emit a signal which tells what is done
		self.log("Done.. emitting signal.","blue")	
		self.emit(self.background_task_signal)
	def finishGridding(self):
		crs = QgsCoordinateReferenceSystem(CRS_CODE, QgsCoordinateReferenceSystem.EpsgCrsId)
		self.log(crs.toProj4())
		for path,name in zip(self.grid_paths,self.grid_layer_names):
			grid_layer=QgsRasterLayer(path,name)
			grid_layer.setCrs(crs,False)
			QgsMapLayerRegistry.instance().addMapLayer(grid_layer)
	#end gridding stuff	
	@pyqtSignature('')
	def on_bt_add_polygon_layer_clicked(self):
		layer_name="tmp_poly_{0:d}".format(self.n_temp_polys)
		self.n_temp_polys+=1
		vector_layer=QgsVectorLayer("Polygon?crs="+DEF_CRS,layer_name,"memory")
		QgsMapLayerRegistry.instance().addMapLayer(vector_layer)
		self.polygon_layer_ids=self.refreshPolygonLayers(self.cb_polygonlayers)
		vector_layer.startEditing()
		
	#TODO: fix that layer boxes dont get updated after layer has been added....
	@pyqtSignature('')
	def on_bt_add_line_layer_clicked(self):
		layer_name="tmp_line_{0:d}".format(self.n_temp_lines)
		self.n_temp_lines+=1
		vector_layer=QgsVectorLayer("LineString?crs="+DEF_CRS,layer_name,"memory")
		QgsMapLayerRegistry.instance().addMapLayer(vector_layer)
		self.line_layer_ids=self.refreshLineLayers(self.cb_linelayers)
		vector_layer.startEditing()
		
	@pyqtSignature('')
	def on_bt_plot3d_clicked(self):
		self.plotNow(dim=3)
	@pyqtSignature('')
	def on_bt_plot2d_clicked(self):
		#get input#
		self.plotNow(dim=2)
	@pyqtSignature('')
	def on_bt_plot_vertical_clicked(self):
		#get input#
		self.plotNow(dim=1)
	@pyqtSignature('')
	def on_bt_dump_csv_clicked(self):
		#A two step background process...
		self.txt_log.clear()
		data_ok,thread_started=self.getPointcloudAndVectors(2,self.startDumpCsv)
		if data_ok:
			self.startDumpCsv()
	def startDumpCsv(self):
		if self.pc_in_poly is None:
			return
		f_name=unicode(QFileDialog.getSaveFileName(self, "Select an output file name for the csv file",self.dir,"*.csv"))
		if f_name is None or len(f_name)==0:
			return
		try:
			f=open(f_name,"w")
		except Exception,e:
			self.log(str(e),"red")
			return
		self.csv_file_name=f_name
		self.runInBackground(self.dumpCsv,self.finishCsv,(f,))
	def dumpCsv(self,f):
		log_progress=lambda c : self.log("{0:d}".format(c),"blue")
		self.pc_in_poly.dump_csv(f,log_progress)
		f.close()
		self.emit(self.background_task_signal)
	def finishCsv(self):
		if self.csv_file_name is not None and self.chb_add_csv.isChecked():
			self.log("Work in progress... does not work right now...","orange")
			lname=os.path.basename(os.path.splitext(self.csv_file_name)[0])+"_csv"
			vector_layer=QgsVectorLayer(self.csv_file_name,lname,"delimitedtext")
			QgsMapLayerRegistry.instance().addMapLayer(vector_layer)
			
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
	def loadPointcloud(self,wkt,arr,index_layer):
		#load a pointcloud from a 2d-numpy array... (xy-verts)
		#To be run in background - sets self.pc_in_poly
		#somehow a qgs_geom does not seem to be valid in between threads.... thus we pass a wkt-representation...
		try:
			x1,y1=arr[0].min(axis=0)
			x2,y2=arr[0].max(axis=0)
			found=[]
			qgs_geom=QgsGeometry.fromWkt(wkt)
			feats=index_layer.getFeatures(QgsFeatureRequest(qgs_geom.boundingBox()))
			for feat in feats:
				geom_other=feat.geometry()
				if geom_other.intersection(qgs_geom).area()>1e-5:
					try:
						path=feat.attribute(INDEX_PATH_FIELD)
					except KeyError:
						self.log("Selected las index does not have any {0:s} field".format(INDEX_PATH_FIELD),"red")
						self.emit(self.background_task_signal)
						return
					#self.log(path)
					if os.path.exists(path):
						found.append(path)
					else:
						self.log("{0:s} does not exist!".format(path),"red")
			self.log("Found {0:d} las file(s) that intersects polygon...".format(len(found)))
			if len(found)==0:
				self.log("Didn't find any las files :-(","red")
				self.pc_in_poly=None
				self.emit(self.background_task_signal)
				return
			xy=np.empty((0,2),dtype=np.float64)
			z=np.empty((0,),dtype=np.float64)
			c=np.empty((0,),dtype=np.int32)
			pid=np.empty((0,),dtype=np.int32)
			for las_name in found:
				self.log("Loading "+las_name,"blue")
				#check if we have pc in memory...
				if self.pc is not None and self.pc_path==las_name:
					pc=self.pc
					self.log("Loading tile from memory buffer..","blue")
				else:
					
					try:
						pc=pointcloud.fromLAS(las_name)
					except Exception,e:
						self.log(str(e))
						continue
				#check if we should buffer pc in memory
				if self.chb_buffer_in_mem.isChecked():
					self.pc=pc
					self.pc_path=las_name
				else:
					self.pc=None
					self.pc_path=None
				pcp=pc.cut_to_polygon(arr)
				if xy.shape[0]>1e6:
					self.log("Already too many points to plot!","orange")
					continue
				xy=np.vstack((xy,pcp.xy))
				z=np.append(z,pcp.z)
				c=np.append(c,pcp.c)
				pid=np.append(pid,pcp.pid)
			if xy.shape[0]==0:
				self.log("Hmmm - something wrong. No points loaded...","red")
				self.pc_in_poly=None
				self.emit(self.background_task_signal)
				return
			#success - set point cloud...
			self.pc_in_poly=pointcloud.Pointcloud(xy,z,c,pid)
		except Exception,e:
			self.log("A background exception occurred:\n"+str(e),"red")
		self.emit(self.background_task_signal)
	def getPointcloudAndVectors(self,dim,method_on_finish):
		#Method to call whenever we need to do something with the pointcloud - checks if we should reload, etc.
		#This method should return signals: data_ready, thread_is_started
		index_layer_name=self.cb_indexlayers.currentText()
		index_layer_index=self.cb_indexlayers.currentIndex()
		if index_layer_name is None or len(index_layer_name)==0:
			self.message("Please select or create a las file index first")
			return False,False
		#check if this is a new id....!
		index_layer_id=self.index_layer_ids[index_layer_index]
		is_new=(self.index_layer is None or self.index_layer.id()!=index_layer_id)
		index_layer=QgsMapLayerRegistry.instance().mapLayer(index_layer_id)
		if is_new:
			#new index - so reset other attrs
			self.pc_in_poly=None
			self.poly_array=None
			self.line_array=None
			self.index_layer=index_layer
			self.log("New index layer selected...","blue")
		if index_layer is None:
			self.log("No index layer by that id...: "+index_layer_id,"red")
			return False,False
		if dim>=2:
			vlayer_name=self.cb_polygonlayers.currentText() #should alwyas be '' if no selection
			gtype="polygon"
			ltype=QGis.Polygon
			ids=self.polygon_layer_ids
			layer_index=self.cb_polygonlayers.currentIndex()
		else:
			vlayer_name=self.cb_linelayers.currentText() #should alwyas be '' if no selection
			gtype="line"
			ltype=QGis.Line
			ids=self.line_layer_ids
			layer_index=self.cb_linelayers.currentIndex()
		if vlayer_name is None or len(vlayer_name)==0:
			self.log("No "+gtype+" layers loaded!","red")
			return False,False
		layer_id=ids[layer_index]
		layer=QgsMapLayerRegistry.instance().mapLayer(layer_id)
		if layer is None:
			self.log("No layer named "+vlayer_name+" id: "+layer_id,"red")
			return None,None,None
		n_selected=layer.selectedFeatureCount()
		if n_selected==0:
			self.log("Select at lest one feature from "+vlayer_name,"red")
			return False,False
		if n_selected>1:
			self.log("More than one feature selected - using the first one...","orange")
		
		feat=layer.selectedFeatures()[0]
		geom=feat.geometry()
		ogr_geom=ogr.CreateGeometryFromWkt(str(geom.exportToWkt()))
		if dim<2:
			if ogr_geom.GetDimension()!=1:
				self.log("Selected feature is not a line!","red")
				return None,None,None
			buf_dist=float(self.spb_buffer_dist.value())
			self.log("Buffering with distance {0:.2f}".format(buf_dist),"blue")
			self.line_array=array_geometry.ogrline2array(ogr_geom)
			ogr_geom=ogr_geom.Buffer(buf_dist)
			geom=QgsGeometry.fromWkt(ogr_geom.ExportToWkt())
		arr=array_geometry.ogrpoly2array(ogr_geom)
		if DEBUG:
			self.log("{0:.2f}".format(geom.boundingBox().xMinimum()),"green")
			self.log("{0:.2f}".format(geom.boundingBox().xMaximum()),"green")
			self.log("{0:.2f}".format(geom.boundingBox().yMinimum()),"green")
			self.log("{0:.2f}".format(geom.boundingBox().yMaximum()),"green")
		if (self.pc_in_poly is None) or (self.poly_array is None) or (not self.polysEqual(arr,self.poly_array)):
			#polygon has changed! or pc not loaded...
			self.poly_array=arr
			self.log("Loading pointcloud...","blue")
			#somehow the qgs_geom seems to be invalid to pass between threads... hmmm...
			self.runInBackground(self.loadPointcloud,method_on_finish,(geom.exportToWkt(),self.poly_array,self.index_layer))
			return False,True #data is not ready, but thread started
		return True,False #data is ready no thread started
		
			
	def getLasFiles(self,path):
		do_walk=self.chb_walk_folders.isChecked()
		path=path.replace("*.las","")
		if do_walk:
			lasfiles=[]
			for root,dirs,files in os.walk(path):
				for name in files:
					if name.endswith(".las") or name.endswith(".laz"):
						lasfiles.append(os.path.join(root,name))
						if len(lasfiles)%500==0:
							self.log("{0:d} las files found...".format(len(lasfiles)),"blue")
						
		else:
			lasfiles=glob.glob(os.path.join(path,"*.las"))
			lasfiles.extend(glob.glob(os.path.join(path,"*.laz")))
		return lasfiles
	def coord2KmName(self,x,y):
		E="{0:d}".format(int(x/1e3))
		N="{0:d}".format(int(y/1e3))
		return N+"_"+E
	def plotNow(self,dim=2):
		self.txt_log.clear()
		self.plot_dim=dim  #remember this for the finish_method
		data_ok,thread_started=self.getPointcloudAndVectors(dim,self.finishPlotNow)
		if data_ok:
			self.finishPlotNow()
	def finishPlotNow(self):
		#sloppy shortcuts...
		pc=self.pc_in_poly
		dim=self.plot_dim
		arr=self.poly_array
		line_arr=self.line_array
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
			title=""
		if pc.get_size()==0:
			self.log("Sorry no points in polygon!","orange")
			if self.chb_restrict.isChecked():
				self.log("Perhaps select another z-interval... :)","orange")
			return
		if dim>1:
			self.log("Plotting in dimension: "+str(dim),"blue")
		else:
			self.log("Plotting vertical section","blue")
		by_strips=self.chb_strip_color.isChecked()
		axis_equal=self.chb_axis_equal.isChecked()
		show_numbers=self.chb_show_numbers.isChecked()  #show numbers on plot?
		if by_strips:
			self.log("Coloring by strip id","blue")
		if dim==2:
			plot2d(pc,arr,title,by_strips=by_strips,show_numbers=show_numbers)
		elif dim==3:
			if pc.get_size()>2*1e5:
				self.log("Oh no - too many points for that!","orange")
				return
			plot3d(pc,title,by_strips=by_strips)
		else:
			if line_arr.shape[0]>2:
				self.log("Warning: more than two vertices in line - for now we'll only plot 'along' end vertices as the 'axis'","orange")
			title+=" bbox: {0:s}".format(str(pc.get_bounds()))
			plot_vertical(pc,line_arr,title,by_strips=by_strips,axis_equal=axis_equal,show_numbers=show_numbers)

	def message(self,text,title="Error"):
		QMessageBox.warning(self,title,text)
	def log(self,text,color="black"):
		self.txt_log.setTextColor(QColor(color))
		self.txt_log.append(text)
		

	