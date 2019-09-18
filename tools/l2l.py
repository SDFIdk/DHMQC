# Copyright (c) 2015-2016, Danish Geodata Agency <gst@gst.dk>
# Copyright (c) 2016, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
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
from __future__ import absolute_import
from __future__ import print_function
import os,sys
from osgeo import ogr
import argparse
parser=argparse.ArgumentParser(description="Write a batch file to drop strips based on input layers")
parser.add_argument("tile_layer",help="Layer containing tiles with path attribute")
parser.add_argument("path_attr",help="Name of path to las-tile attribute")
parser.add_argument("strip_layer",help="Layer containing strips to be dropped")
parser.add_argument("strip_attr",help="Name of strip-id attribute")
parser.add_argument("outfile",help="Path to output shell script")
parser.add_argument("-outfolder",help="Path to output folder for modified las-files",default="")
parser.add_argument("-binpath",help="Absolute Path to bin folder of lastools.",default="")
parser.add_argument("-strip",help="Extra strip to add",type=int)
def main(args):
	pargs=parser.parse_args(args[1:])
	f=open(pargs.outfile,"w")
	paths=set()
	pids=set()
	ds=ogr.Open(pargs.tile_layer)
	layer=ds.GetLayer(0)
	nf=layer.GetFeatureCount()
	for i in xrange(nf):
		feat=layer.GetNextFeature()
		path=feat.GetFieldAsString(pargs.path_attr)
		paths.add(path)
	print(("%d unique tiles." %(len(paths))))
	layer=None
	ds=None
	ds=ogr.Open(pargs.strip_layer)
	layer=ds.GetLayer(0)
	nf=layer.GetFeatureCount()
	for i in xrange(nf):
		feat=layer.GetNextFeature()
		pid=feat.GetFieldAsInteger(pargs.strip_attr)
		pids.add(pid)
	print(("%d unique strip ids." %(len(pids))))
	layer=None
	ds=None
	drop_pids=""
	for pid in pids:
		drop_pids+=" -drop_point_source %d" %pid
	if pargs.strip:
		drop_pids+=" -drop_point_source %d" %pargs.strip
	las2las=os.path.join(pargs.binpath,"las2las")
	for path in paths:
		out=os.path.join(pargs.outfolder,os.path.basename(path))
		f.write(las2las+" -i %s -o %s %s\n" %(path,out,drop_pids))
	f.close()
	

if __name__=="__main__":
	main(sys.argv)
	
		

