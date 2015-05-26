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
######################################################################################
## Spike check: check for steep somewhat isolated triangles...
## work in progress...
######################################################################################
import sys,os,time
from thatsDEM import pointcloud, vector_io, array_geometry
from db import report
import numpy as np
import dhmqc_constants as constants
from utils.osutils import ArgumentParser
DEBUG="-debug" in sys.argv
if DEBUG:
    import matplotlib
    matplotlib.use("Qt4Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D

#DEFAULT CLASS
cut_to=constants.terrain #default to terrain only...

#LIMITS FOR STEEP EDGES
slope_min=25 #minumum this in degrees
zlim=0.1 #minimum this in meters
#SPATIAL INDEX
filter_rad=1.5


#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__)

#Argument handling
parser=ArgumentParser(description="Check for spikes - a spike is a point with steep edges in all four quadrants (all edges should be steep unless those 'close').",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
parser.add_argument("-class",dest="cut_class",type=int,default=cut_to,help="Inspect points of this class - defaults to 'terrain'")
parser.add_argument("-slope",dest="slope",type=float,default=slope_min,help="Specify the minial slope in degrees of a steep edge (0-90 deg) - default 25 deg.")
parser.add_argument("-zlim",dest="zlim",type=float,default=zlim,help="Specify the minial (positive) delta z of a steep edge - default 0.1 m")
parser.add_argument("-debug",action="store_true",dest="debug",help="Set debug mode (plotting)")
parser.add_argument("las_file",help="input 1km las tile.")



def plot3d(xy,z,x1,y1,z1):
    fig = plt.figure()
    ax = Axes3D(fig)
    ax.scatter(xy[:,0], xy[:,1], z,s=1.7)
    ax.scatter(x1, y1, z1,s=4.0,color="red")
    plt.show()
    
def usage():
    parser.print_help()
    
            

def main(args):
    pargs=parser.parse_args(args[1:])
    lasname=pargs.las_file
    kmname=constants.get_tilename(lasname)
    print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
    if pargs.schema is not None:
        report.set_schema(pargs.schema)
    reporter=report.ReportSpikes(pargs.use_local)
    if pargs.zlim<0:
        print("zlim must be positive!")
        usage()
    if (pargs.slope<0 or pargs.slope>=90):
        print("Specify a slope angle in the range 0->90 degrees.")
        usage()
    cut_class=pargs.cut_class
    print("Cutting to class (terrain) {0:d}".format(cut_class))
    pc=pointcloud.fromLAS(lasname).cut_to_class(cut_class)
    if pc.get_size()<10:
        print("Too few points in pointcloud.")
        return
    print("Sorting spatially...")
    pc.sort_spatially(filter_rad)
    slope_arg=np.tan(np.radians(pargs.slope))**2
    print("Using steepnes parameters: angle: {0:.2f} degrees, delta-z: {1:.2f}".format(pargs.slope,pargs.zlim))
    print("Filtering, radius: {0:.2f}".format(filter_rad))
    dz=pc.spike_filter(filter_rad,slope_arg,pargs.zlim)
    M=(dz!=0)
    dz=dz[M]
    pc=pc.cut(M)
    print("Spikes: {0:d}".format(M.sum()))
    for i in range(pc.size): #todo - define __iter__
        x,y=pc.xy[i]
        z=pc.z[i]
        mdz=dz[i]
        c=pc.c[i]
        pid=pc.pid[i]
        print("spike: x: {0:.2f} y: {1:.2f} mean-dz: {2:.2f}".format(x,y,mdz))
        wkt_geom="POINT({0:.2f} {1:.2f})".format(x,y)
        reporter.report(kmname,filter_rad,mdz,x,y,z,c,pid,wkt_geom=wkt_geom)
    
    

if __name__=="__main__":
    main(sys.argv)
    