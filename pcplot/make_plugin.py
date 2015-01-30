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
		print("Directory "+plugin_path+" already exists. Overwriting!")
		try:
			shutil.rmtree(plugin_path)
		except Exception,e:
			print(str(e))
			return
	shutil.copytree(here,plugin_path)
	shutil.copytree(os.path.join(here,"..","qc","thatsDEM"),os.path.join(plugin_path,"thatsDEM"))
	shutil.copytree(os.path.join(here,"..","qc","lib"),os.path.join(plugin_path,"lib"))
	

if __name__=="__main__":
	main(sys.argv)
	
