##############
## Delete tiles from an ogr-layer
################
import os,sys,time
import shutil
from osgeo import ogr
from argparse import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
parser=ArgumentParser(description="Delete tiles with path attribute from an ogr-layer")
parser.add_argument("tilelayer",help="ogr-layer containing tiles to be deleted")
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
	s=raw_input("Are you sure you want to delete all these tiles (YES)?")
	if s.strip()!="YES":
		print("OK - quitting.")
		return
	for name in tilelist:
		print(name)
		outname=os.path.join(pargs.outdir,os.path.basename(name))
		shutil.copy(name,outname)



if __name__=="__main__":
	main(sys.argv)