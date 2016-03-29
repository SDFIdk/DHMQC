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

"""


"""
import sys
import os
import subprocess
import time

from utils.osutils import ArgumentParser
import xml.etree.ElementTree as ET

import dhmqc_constants as constants
from utils.wmsfetch import get_georef_image_wms

progname=os.path.basename(__file__).replace(".pyc",".py")

parser = ArgumentParser(description='Use PDAL filters to fill RGB values in las/laz file from ortophoto downloaded from WMS', prog=progname)

parser.add_argument('las_file', help='Input las file')
parser.add_argument('out_dir', help='Output directory')
parser.add_argument('-wms_url', help='URL to WMS Capabilitites file')
parser.add_argument('-wms_layer', default='', help='Layer from WMS service')
parser.add_argument('-px_size', type=float, default=1.0, help='Pixel size of retrived WMS image')

def usage():
    parser.print_help()


def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception as e:
        print(str(e))
        return 1

    kmname = constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))

    tif_image = kmname + '.tif'

    if not os.path.exists(pargs.out_dir):
        print pargs.out_dir
        os.makedirs(os.path.abspath(pargs.out_dir))

    # Get image from WMS
    get_georef_image_wms(kmname, pargs.wms_url, pargs.wms_layer, tif_image, pargs.px_size)

    # apply colorization filter with pdal translate
    out_file = os.path.join(pargs.out_dir, os.path.basename(pargs.las_file))
    call = 'pdal translate -i %s -o %s --filter filters.colorization --filters.colorization.raster=%s' % (pargs.las_file, out_file, tif_image)
    subprocess.call(call)

    # clean up...
    os.remove(tif_image)

if __name__ == '__main__':
    main(sys.argv)
