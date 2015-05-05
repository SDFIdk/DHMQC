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
#########################################
## Stupid wrapper to hillshade tiles.. reads a buffer around each tile - 1px should be sufficient to remove edges...
## Will reduce hillshade output size A LOT For 'scattered' tiles. Build a vrt of output... 
############################################
import os,sys,time
import shlex, subprocess
from osgeo import ogr
import xml.etree.ElementTree as ET
buf=2  #2pix buffer
from argparse import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)

parser=ArgumentParser(description="Hillshade a subtiles of a vrt dataset with buffering")
parser.add_argument("-tmpdir",help="Directory to store temporary files. If not given will be set to dirname of vrtfile")
parser.add_argument("-outdir",help="Output directory. If not given  be set to dirname of vrtfile")
parser.add_argument("-overwrite",action="store_true",help="If set and output file exists it will be overwritten. Otherwise the process will just skip that tile.")
parser.add_argument("-tiles",help="Input layer of tiles to do - if basename equals a basename in the vrt: do the tile")
parser.add_argument("-attr",help="Path / basename attributte of input layer. - defaults to 'path'",default="path")
parser.add_argument("-youngerthan",type=int,help="Overwrite files younger than <specify_time_in_seconds>")
#add some arguments below
parser.add_argument("vrt_file",help="input virtual dataset container")
PID=str(os.getpid())
HILLCMD="gdaldem hillshade -z 3.0 -s 1.0 -az 315.0 -alt 37.0 -of GTiff -co TILED=YES -co COMPRESS=DEFLATE -co PREDICTOR=2 "
#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
SHLEX_POSIX=(os.name=="posix")
def usage():
	parser.print_help()
	


def main(args):
	pargs=parser.parse_args(args[1:])
	vrt=ET.parse(pargs.vrt_file)
	root=vrt.getroot()
	ncols=int(root.attrib["rasterXSize"])
	nrows=int(root.attrib["rasterYSize"])
	band=root.find("VRTRasterBand")
	files=band.findall("ComplexSource")
	tmpdir=pargs.tmpdir
	tilelist=None
	if pargs.tiles is not None:
		tilelist=[]
		ds=ogr.Open(pargs.tiles)
		layer=ds.GetLayer(0)
		nf=layer.GetFeatureCount()
		for i in range(nf):
			feat=layer.GetNextFeature()
			path=feat.GetFieldAsString(pargs.attr)
			tilelist.append(os.path.basename(path))
		layer=None
		ds=None
		print("%d filenames in %s" %(len(tilelist),pargs.tiles))
	if tmpdir is None:
		tmpdir=os.path.dirname(pargs.vrt_file)
	outdir=pargs.outdir
	if outdir is None:
		outdir=os.path.dirname(pargs.vrt_file)
	
	ndone=0
	for elem in files:
		path=elem.find("SourceFilename")
		basename=os.path.basename(path.text)
		if tilelist is not None:
			try:
				i=tilelist.index(basename)
			except:
				continue
			tilelist.pop(i)
		tilename=os.path.splitext(basename)[0]
		outname=os.path.join(outdir,tilename+"_hs.tif")
		if os.path.exists(outname):
			skip=True
			if pargs.overwrite:
				skip=False
			if pargs.youngerthan is not None:
				age=time.time()-os.path.getmtime(path.text)
				if age<pargs.youngerthan:
					skip=False
					print(tilename+" is deemed young enough...")
			if skip:
				continue
			os.remove(outname)
		tmptile=os.path.join(tmpdir,tilename+"_tmp_"+PID+".tif")
		tmphilltile=os.path.join(tmpdir,tilename+"_tmp_hs_"+PID+".tif")
		rect=elem.find("DstRect")
		xoff=int(rect.attrib["xOff"])
		yoff=int(rect.attrib["yOff"])
		xwin=int(rect.attrib["xSize"])
		ywin=int(rect.attrib["ySize"])
		if xoff>0:
			bleft=buf
		else:
			bleft=0
		if yoff>0:
			btop=buf
		else:
			btop=0
		if (xoff+xwin)<ncols:
			bright=buf
		else:
			bright=0
		if (yoff+ywin)<nrows:
			blow=buf
		else:
			blow=0
		cmd="gdal_translate -srcwin {0:d} {1:d} {2:d} {3:d} ".format(xoff-bleft,yoff-btop,xwin+bleft+bright,ywin+blow+btop)+pargs.vrt_file+" "+tmptile
		print(cmd)
		subprocess.call(shlex.split(cmd,posix=SHLEX_POSIX))
		cmd=HILLCMD+tmptile+" "+tmphilltile
		print(cmd)
		subprocess.call(shlex.split(cmd,posix=SHLEX_POSIX))
		cmd="gdal_translate -srcwin {0:d} {1:d} {2:d} {3:d} ".format(bleft,btop,xwin,ywin)+tmphilltile+" "+outname
		print(cmd)
		subprocess.call(shlex.split(cmd,posix=SHLEX_POSIX))
		os.remove(tmptile)
		os.remove(tmphilltile)
		ndone+=1
	print("Did %d tiles" %ndone) 
	
	

#to be able to call the script 'stand alone'
if __name__=="__main__":
	main(sys.argv)
		
		
		
	