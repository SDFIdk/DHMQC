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

'''
colorize.py - Add colors to las-files.

Overwrite near-black RGB-points in las-files with colors from a WMS. In case
the las-file uses a dataformat ID that does not have include RGB-values, RGB-
values will be attached to all points in the file. Again the source of the
coloring are a WMS.

The coloring is powered by PDAL behind the scenes. The PDAL executable has to
be in the system path, otherwise the script will fail.

'''
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import subprocess
import time
import json

from .utils.osutils import ArgumentParser
import laspy

from . import dhmqc_constants as constants
from .utils.wmsfetch import get_georef_image_wms

PDAL = 'pdal'

progname=os.path.basename(__file__).replace(".pyc",".py")

parser = ArgumentParser(
    description='Add RGB-values from a WMS to near-black points in las-files',
    prog=progname
)

parser.add_argument('las_file', help='Input las file')
parser.add_argument('out_dir', help='Output directory')
parser.add_argument('-wms_url', help='URL to WMS Capabilitites file')
parser.add_argument('-wms_layer', default='', help='Layer from WMS service')
parser.add_argument('-px_size', type=float, default=1.0, help='Pixel size of retrived WMS image')

def usage():
    parser.print_help()

def create_pdal_pipeline(json_out, las_in, las_out, raster):

    with laspy.file.File(las_in, mode='r') as las:
        dataformat_id = las.header.data_format_id

    reader = {
        'type':'readers.las',
        'filename':'{0}'.format(las_in),
        'spatialreference':'EPSG:25832',
        'tag': 'in'
    }

    if dataformat_id == 3:
        # if the las file already has colors we only want to add colors to the
        # points that are near-black. Points that already has non-black colors
        # will not be touched, as the RGB-values from the sensor are much more
        # accurate.
        coloring = [
            {
                'type': 'filters.range',
                'limits': 'Red[512:65535],Green[512:65535],Blue[512:65535]',
                'inputs': 'in',
                'tag': 'has_colors'
            },
            {
                'type': 'filters.range',
                'limits': 'Red[0:511],Green[0:511],Blue[0:511]',
                'inputs': 'in',
                'tag': 'no_colors'
            },
            {
                'type': 'filters.colorization',
                'raster': '{0}'.format(raster),
                'dimensions': 'Red:1:256.0, Green:2:256.0, Blue:3:256.0',
                'inputs': 'no_colors',
                'tag': 'colorized'
            },
            {
                'type': 'filters.merge',
                'inputs': ['has_colors', 'colorized'],
                'tag': 'all_colors'
            }
        ]
    else:
        # if no RGB-values are present in the file we want to apply them to all
        # points. Hence we don't a fork in the pipeline as above.
        coloring = [
            {
                'type': 'filters.colorization',
                'raster': '{0}'.format(raster),
                'dimensions': 'Red:1:256.0, Green:2:256.0, Blue:3:256.0',
                'inputs': 'in',
                'tag': 'all_colors'
            }
        ]

    writer = {
        'type': 'writers.las',
        'inputs': 'all_colors',
        'dataformat_id': 3,
        'minor_version': 3,
        'system_id': 'MODIFICATION',
        'filename':'{0}'.format(las_out)
    }

    pipeline = []
    pipeline.append(reader)
    pipeline.extend(coloring)
    pipeline.append(writer)

    with open(json_out, 'w') as fp:
        json.dump({'pipeline': pipeline}, fp, indent=4, separators=(',', ': '))


def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception as e:
        print((str(e)))
        return 1

    kmname = constants.get_tilename(pargs.las_file)
    print(("Running %s on block: %s, %s" % (progname,kmname,time.asctime())))

    tif_image = kmname + '.tif'
    out_file = os.path.join(pargs.out_dir, os.path.basename(pargs.las_file))

    if not os.path.exists(pargs.out_dir):
        print(pargs.out_dir)
        os.makedirs(os.path.abspath(pargs.out_dir))

    # Get image from WMS
    get_georef_image_wms(kmname, pargs.wms_url, pargs.wms_layer, tif_image, pargs.px_size)

    # create pipeline
    pipeline = 'temp_{tile}.json'.format(tile=kmname)
    create_pdal_pipeline(pipeline, pargs.las_file, out_file, tif_image)

    # apply colorization filter with pdal translate
    call = '{pdal_bin} pipeline {json_pipeline}'.format(pdal_bin=PDAL, json_pipeline=pipeline)
    subprocess.call(call)

    # clean up...
    os.remove(tif_image)
    os.remove(pipeline)
    return 0

if __name__ == '__main__':
    main(sys.argv)
