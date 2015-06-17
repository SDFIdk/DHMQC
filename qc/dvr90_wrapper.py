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
import dhmqc_constants as constants
from utils.osutils import ArgumentParser,run_command  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
GEOID_GRID=os.path.realpath(os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b.utm32"))
BIN_DIR=os.path.realpath(os.path.join(os.path.dirname(__file__),"lib"))
DVR90=os.path.join(BIN_DIR,"DVR90")
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")
if sys.platform.startswith("win"):
    os.environ["PATH"]+=";"+BIN_DIR
#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Warp las/laz file from ellipsoidal heights to orthometric heights.",prog=progname)
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("outdir",help="Output folder.")


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
    if not os.path.exists(pargs.outdir):
        os.mkdir(pargs.outdir)
    cmd=[DVR90,"-N",GEOID_GRID,"-o",os.path.join(pargs.outdir,os.path.basename(pargs.las_file)),pargs.las_file]
    rc,stdout,stderr=run_command(cmd)
    if rc!=0:
        print(stderr)
        raise Exception("Weird return code from DVR90: %d" %rc)
    return rc

#to be able to call the script 'stand alone'
if __name__=="__main__":
    main(sys.argv)