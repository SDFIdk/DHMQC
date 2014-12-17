##############
## Copy tiles from an ogr-layer to a dest folder
################
import os,sys,time
import shutil
from osgeo import ogr
from argparse import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
parser=ArgumentParser(description="TODO")
parser.add_argument("tilelayer",help="todo")
parser.add_argument("outdir",help="Output directory.")
parser.add_argument("-attr",help="Path / basename attributte of input layer. - defaults to 'path'",default="path")

def main(args):
	pargs=parser.parse_args(args[1:])
	tilelist=None
	tilelist=[]
	ds=ogr.Open(pargs.tilelayer)
	layer=ds.GetLayer(0)
	nf=layer.GetFeatureCount()
	for i in range(nf):
		feat=layer.GetNextFeature()
		path=feat.GetFieldAsString(pargs.attr)
		tilelist.append(path)
	layer=None
	ds=None
	print("%d filenames in %s" %(len(tilelist),pargs.tilelayer))
	for name in tilelist:
		print(name)
		outname=os.path.join(pargs.outdir,os.path.basename(name))
		shutil.copy(name,outname)



if __name__=="__main__":
	main(sys.argv)
	
	