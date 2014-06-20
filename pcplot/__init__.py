def classFactory(iface):
	# load TestPlugin class from file testplugin.py
	from PcPlot_plugin import PcPlot_plugin 
	return PcPlot_plugin(iface)
