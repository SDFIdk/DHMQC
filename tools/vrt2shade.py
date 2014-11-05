#########################################
## Stupid wrapper to hillshade tiles.. reads a buffer around each tile - 1px should be sufficient to remove edges...
## Will reduce hillshade output size A LOT For 'scattered' tiles. Build a vrt of output... 
############################################
import os,sys,time
import shlex, subprocess
import xml.etree.ElementTree as ET
buf=2  #2pix buffer
from argparse import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)

parser=ArgumentParser(description="Hillshade a subtiles of a vrt dataset with buffering")
parser.add_argument("-tmpdir",help="Directory to store temporary files. If not given will be set to dirname of vrtfile")
parser.add_argument("-outdir",help="Output directory. If not given  be set to dirname of vrtfile")
parser.add_argument("-overwrite",action="store_true",help="If set and output file exists it will be overwritten. Otherwise the process will just skip that tile.")
#add some arguments below
parser.add_argument("vrt_file",help="input virtual dataset container")
PID=str(os.getpid())
HILLCMD="gdaldem hillshade -z 3.0 -s 1.0 -az 315.0 -alt 37.0 -of GTiff -co TILED=YES -co COMPRESS=DEFLATE -co PREDICTOR=2 "
#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
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
	
	if tmpdir is None:
		tmpdir=os.path.dirname(pargs.vrt_file)
	outdir=pargs.outdir
	if outdir is None:
		outdir=os.path.dirname(pargs.vrt_file)
	
	
	for elem in files:
		path=elem.find("SourceFilename")
		tilename=os.path.splitext(os.path.basename(path.text))[0]
		outname=os.path.join(outdir,tilename+"_hs.tif")
		if os.path.exists(outname):
			if not pargs.overwrite:
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
		subprocess.call(shlex.split(cmd))
		cmd=HILLCMD+tmptile+" "+tmphilltile
		print(cmd)
		subprocess.call(shlex.split(cmd))
		cmd="gdal_translate -srcwin {0:d} {1:d} {2:d} {3:d} ".format(bleft,btop,xwin,ywin)+tmphilltile+" "+outname
		print(cmd)
		subprocess.call(shlex.split(cmd))
		os.remove(tmptile)
		os.remove(tmphilltile)
	
	

#to be able to call the script 'stand alone'
if __name__=="__main__":
	main(sys.argv)
		
		
		
	