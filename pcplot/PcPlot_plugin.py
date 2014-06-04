#!python
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# initialize Qt resources from file resouces.py
import resources
import PcPlot_dialog
class PcPlot_plugin:
	def __init__(self, iface):
		# save reference to the QGIS interface
		self.iface = iface
	def initGui(self):
		# create action that will start plugin configuration
		self.action = QAction(QIcon(":/plugins/pcplot/icon.ico"), "PcPlot", self.iface.mainWindow())
		self.action.setWhatsThis("Configuration for plugin")
		#self.action.setStatusTip("This is status tip")
		QObject.connect(self.action, SIGNAL("triggered()"), self.run)
		# add toolbar button and menu item
		self.iface.addToolBarIcon(self.action)
		self.iface.addPluginToMenu("&PcPlot", self.action)
		
	def unload(self):
		# remove the plugin menu item and icon
		self.iface.removePluginMenu("&PcPlot",self.action)
		self.iface.removeToolBarIcon(self.action)
		# disconnect form signal of the canvas
		
	def run(self):
		# create and show a configuration dialog or something similar
		dlg=PcPlot_dialog.PcPlot_dialog(self.iface)
		dlg.show()
		result = dlg.exec_() 
		

