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
##  TEMPLATE FOR A TEST TO BE WRAPPED 
##  FILL IN AND DELETE BELOW...
######################################################################################
import sys,os,time
#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry
from db import report
import numpy as np
import dhmqc_constants as constants
from utils.osutils import ArgumentParser,run_command  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
z_min=1.0
cut_to=constants.terrain
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")
HAYSTACK=os.path.join(os.path.dirname(__file__),"lib","haystack")
#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Use haystack to add some points to a las file (filling holes).",prog=progname)
parser.add_argument("-olaz",help="Output as laz (will store a temporary file and translate that)",action="store_true")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("-a",dest="add_file",help="Binary file of points to add. Containing doubles in the order: x,y,z,c,pid")
parser.add_argument("-w",dest="remove_file",help="Binary file of points to reclassify as noise. Containing doubles in the order: x,y,z,c,pid")
parser.add_argument("outdir",help="Output directory - if using laz output it better be a local (SSD) drive to avoid too much io.")



#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
def usage():
    parser.print_help()
    

def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception,e:
        print(str(e))
        return 1
    kmname=constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
    if pargs.add_file is None and pargs.remove_file is None:
        print("Nothing to do, use -a <file> or -w <file>")
        return 1
    for name in [pargs.add_file,pargs.remove_file]:
        assert(name is None or os.path.exists(name))
    if not os.path.exists(pargs.outdir):
        os.mkdir(pargs.outdir)
    if pargs.olaz:
        ext=".laz"
    else:
        ext=".las"
    outname=os.path.join(pargs.outdir,os.path.splitext(os.path.basename(pargs.las_file))[0])+ext
    cmd=[HAYSTACK,"-o",outname]
    if pargs.add_file is not None:
        print("Adding (as ground)"+pargs.add_file)
        cmd+=["-a",pargs.add_file]
    if pargs.remove_file is not None:
        print("Removing (to withheld and class high_noise) "+pargs.remove_file)
        cmd+=["-w",pargs.remove_file]
    cmd.append(pargs.las_file)
    print(str(cmd))
    rc,stdout,stderr=run_command(cmd)
    if rc!=0:
        print("Something went wrong, stderr:\n"+stderr)
        raise Exception("Haystack error: %d" %rc)
    return 0
        
        
    
    

#to be able to call the script 'stand alone'
if __name__=="__main__":
    main(sys.argv)