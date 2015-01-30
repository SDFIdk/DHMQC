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
		self.action.setWhatsThis("PcPlot plugin for dhmqc")
		#self.action.setStatusTip("This is status tip")
		QObject.connect(self.action, SIGNAL("triggered()"), self.run)
		# add toolbar button and menu item
		self.iface.addToolBarIcon(self.action)
		self.iface.addPluginToMenu("&PcPlot", self.action)
		
	def unload(self):
		# remove the plugin menu item and icon
		self.iface.removePluginMenu("&PcPlot",self.action)
		self.iface.removeToolBarIcon(self.action)
		
		
	def run(self):
		# create and show a configuration dialog or something similar
		dlg=PcPlot_dialog.PcPlot_dialog(self.iface)
		dlg.show()
		result = dlg.exec_() 
		

