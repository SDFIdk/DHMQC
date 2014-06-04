#####################
## Make a Qgis plugin from source code here
######################
import os,sys,shutil,glob
PLUGIN="pcplot"
def usage():
	print("Makes a QGis PcPlot plugin out of source code here...")
	print("Call: %s <plugins_root>" %os.path.basename(sys.argv[0]))
	
def main(args):
	if len(args)<2:
		usage()
	plugin_root=args[1]
	if not os.path.exists(plugin_root):
		print("Sorry - plugin root "+plugin_root+" does not exist!")
		return
	here=os.path.realpath(os.path.dirname(__file__))
	if len(glob.glob(os.path.join(here,"..","qc","lib","lib*")))==0:
		print("Please build dhmqc binaries first!")
		return
	plugin_path=os.path.join(plugin_root,PLUGIN)
	if os.path.exists(plugin_path):
		print("Directory "+plugin_path+" already exists!")
		print("Please remove this first...")
		return
	shutil.copytree(here,plugin_path)
	shutil.copytree(os.path.join(here,"..","qc","thatsDEM"),os.path.join(plugin_path,"thatsDEM"))
	shutil.copytree(os.path.join(here,"..","qc","lib"),os.path.join(plugin_path,"lib"))
	

if __name__=="__main__":
	main(sys.argv)
	
