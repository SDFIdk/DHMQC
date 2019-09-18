from __future__ import print_function
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
##############
## Copy tiles from an ogr-layer to a dest folder
################
from builtins import range
import os,sys,time
import shutil
from osgeo import ogr
from argparse import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
parser=ArgumentParser(description="TODO")
parser.add_argument("tilelayer",help="todo")
parser.add_argument("outdir",help="Output directory.")
parser.add_argument("-dryrun",action="store_true",help="Just show filenames - nothing else..")
group = parser.add_mutually_exclusive_group()
group.add_argument("-attr",help="Path / basename attributte of input layer. - defaults to 'path'",default="path")
group.add_argument("-sql",help="Sql to select relevant file names from a layer (as first attr).")

def main(args):
    pargs=parser.parse_args(args[1:])
    tilelist=None
    tilelist=[]
    ds=ogr.Open(pargs.tilelayer)
    if pargs.sql is None:
        layer=ds.GetLayer(0)
        freq=pargs.attr
    else:
        layer=ds.ExecuteSQL(pargs.sql)
        freq=0
    nf=layer.GetFeatureCount()
    for i in range(nf):
        feat=layer.GetNextFeature()
        path=feat.GetFieldAsString(freq)
        tilelist.append(path)
    layer=None
    ds=None
    print("%d filenames in %s" %(len(tilelist),pargs.tilelayer))
    for name in tilelist:
        outname=os.path.join(pargs.outdir,os.path.basename(name))
        print("From: %s to %s" %(name,outname))
        if not pargs.dryrun:
            shutil.copy(name,outname)



if __name__=="__main__":
    main(sys.argv)
    

