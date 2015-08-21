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
import sys,os,time
#import some relevant modules...
from thatsDEM import grid
import dhmqc_constants as constants
import numpy as np
import scipy.ndimage as im
from osgeo import gdal
import sqlite3 as db
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")
#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Generate hillshade from tiles taking tile edges into account",prog=progname)
parser.add_argument("tile_name",help="Input 1km (dem) tile.")
parser.add_argument("outdir",help="Output directory for hillshades.")
parser.add_argument("-tiledb",help="db - for now created with tile_coverage - of relevant tiles.")
parser.add_argument("-azimuth",help="Specify azimuth, defaults to 315 degrees.",type=float,default=315.0)
parser.add_argument("-height",help="Specify sun height, defaults to 45 degrees.",type=float,default=45.0)
parser.add_argument("-zfactor",help="Specify z-factor (exaggeration)",type=float,default=1.0)
parser.add_argument("-ZT",action="store_true",help="Use Zevenberg-Thorne instead of Horn gradient. Rougher but slightly faster.")
pixel_buf=1
#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
def usage():
    parser.print_help()
    
def get_extended_tile(tile_db,tilename):
    drv=gdal.GetDriverByName("Gtiff")
    con=db.connect(tile_db)
    cur=con.cursor()
    cur.execute("select path,row,col from coverage where tile_name=?",(tilename,))
    data=cur.fetchone()
    path,row,col=data
    print("Reading "+path)
    g0=grid.fromGDAL(path)
    cur.execute("select path,row,col from coverage where abs(row-?)<2 and abs(col-?)<2",(row,col))
    data=cur.fetchall()
    vert_expansions={-1:False,1:False} #top,bottom
    hor_expansions={-1:False,1:False} #left,right
    for path,r,c in data:
        if r==row and c==col:
            continue
        dr=r-row
        dc=c-col
        if dr!=0 and not vert_expansions[dr]:
            #print "vexp",dr
            vert_expansions[dr]=True
            g0.expand_vert(dr,pixel_buf)
            #print g0.geo_ref[3]
        if dc!=0 and not hor_expansions[dc]:
            #print "hexp",dc
            hor_expansions[dc]=True
            g0.expand_hor(dc,pixel_buf)
            #print g0.geo_ref[0]
        print("Reading "+path+" at %d,%d"%(dr,dc))
        #print g0.shape
        ds=gdal.Open(path)
        band=ds.GetRasterBand(1)
        geo_ref=ds.GetGeoTransform()
        assert(geo_ref[1]==g0.geo_ref[1] and geo_ref[5]==g0.geo_ref[5])
        slices0,slices1=grid.intersect_grid_extents(g0.geo_ref,g0.shape,geo_ref,(ds.RasterYSize,ds.RasterXSize))
        assert(slices0 is not None)
        piece=band.ReadAsArray(int(slices1[1].start),int(slices1[0].start),int(slices1[1].stop-slices1[1].start),int(slices1[0].stop-slices1[0].start))
        print(str(piece.shape))
        g0.grid[slices0[0],slices0[1]]=piece
        ds=None
    return g0,vert_expansions,hor_expansions
        
        
                
  


def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception,e:
        print(str(e))
        return 1
    kmname=constants.get_tilename(pargs.tile_name)
    print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
    if pargs.tiledb is not None:
        G,v_expansions,h_expansions=get_extended_tile(pargs.tiledb,kmname)
    else:
        v_expansions=h_expansions={-1:False,1:False}
        G=grid.fromGDAL(pargs.tile_name)
    if pargs.ZT:
        method=1
    else:
        method=0
    H=G.get_hillshade(azimuth=pargs.azimuth,height=pargs.height,method=method)
    for pos in (-1,1):
        if h_expansions[pos]:
            H.shrink_hor(pos,pixel_buf)
        if v_expansions[pos]:
            H.shrink_vert(pos,pixel_buf)
    outname=os.path.join(pargs.outdir,"hs_"+os.path.splitext(os.path.basename(pargs.tile_name))[0]+".tif")
    H.save(outname,dco=["TILED=YES","COMPRESS=DEFLATE","PREDICTOR=2"])
    
    
    
#to be able to call the script 'stand alone'
if __name__=="__main__":
    main(sys.argv)