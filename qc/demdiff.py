import os,sys
import subprocess
import argparse
import shutil


import tempfile
from . import dhmqc_constants as constants

# will do a difference calculation on a 1km tiff file using a reference elevation model (tiff or vrt)
# can be called from a project file containing following statements: 
# TESTNAME="demdiff"
# INPUT_TILE_CONNECTION=r"onetiletif.sqlite"
# TARGS=["F:/GDB/DHM/AnvendelseGIS/DTM_20160318.vrt","c:/slet"]
# print (TARGS)

parser = argparse.ArgumentParser(description="Script for calculating difference between a 1km-tile and a reference tif/vrt")
parser.add_argument("kmname", help="path to the 1km-tile to be tested")
parser.add_argument("reffile", help="path to reference file (can either be tif or vrt) ")
parser.add_argument("output", help="path to output diff files")


#pargs = parser.parse_args()


def main(args):
    '''
    Main function
    '''
    try:
        pargs = parser.parse_args(args[1:])
    except TypeError as error_msg:
        print(str(error_msg))
        return 1
	
    #get the 1km_blah_bla base name
    kmname = constants.get_tilename(pargs.kmname)
	
    try:
        xll, yll, xlr, yul = constants.tilename_to_extent(kmname) #husk at importere fra constants
    except (ValueError, AttributeError) as error_msg:
        print("Exception: %s" % error_msg)
        print("Bad 1km formatting of las file: %s" % kmname)
        return 1
    print ('%s %s %s %s' %(xll, yll, xlr, yul))
	
	
    #create a temp dir (will be deleted later)
    mnt = tempfile.mkdtemp(prefix="diffcalc_")
    
    #and we need a cutout of the ref file - this we store in the temp dir	
    tmpref = os.path.join(mnt,'ref.tif')

    #compose a string for doing gdal_translate - create our local cutout 	
    cmdstr = '''gdal_translate -of GTiff -projwin %s %s %s %s %s %s''' %(xll, yul, xlr, yll, pargs.reffile, tmpref )
    devnull = open(os.devnull, 'w')
    subprocess.call(cmdstr, shell=True, stdout=devnull)

    #now do the actual difference calculation
    onam='diff_'+kmname+'.tif'
    onam = os.path.join(pargs.output,onam)	
    cmdstr = '''gdal_calc --calc="A-B" -A "%s" -B "%s" --outfile="%s"  --creation-option="COMPRESS=DEFLATE" --creation-option="PREDICTOR=3"''' %(pargs.kmname,tmpref,onam)
    subprocess.call(cmdstr, shell=True, stdout=devnull)

    shutil.rmtree(mnt) 
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))