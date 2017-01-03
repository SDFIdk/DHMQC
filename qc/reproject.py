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
reproject.py - Transform coordinates from one spatial reference to another.

Coordinate transformation is powered by PDAL behind the scenes. The PDAL executable has to
be in the system path, otherwise the script will fail.

'''
import sys
import os
import subprocess
import time
import json

from utils.osutils import ArgumentParser

import dhmqc_constants as constants

PDAL = 'pdal'

progname=os.path.basename(__file__).replace(".pyc",".py")

parser = ArgumentParser(
    description='Reproject coordinates in a LAS file.',
    prog=progname
)

parser.add_argument('las_file', help='Input las file')
parser.add_argument('out_dir', help='Output directory')
parser.add_argument(
    '-in_srs',
    default=None,
    help='''Spatial reference of coordinates in input LAS file. Can be any SRS accepted by GDAL.
            Optional when a spatial reference already exists in the input LAS file.''',
)
parser.add_argument(
    '-out_srs',
    required=True,
    help='Spatial reference of coordinates in output LAS file. Can be any SRS accepted by GDAL.',
)
parser.add_argument(
    '-a_srs',
    required=True,
    help='''Assign spatial reference. EPSG code of spatial reference in output las file.
            Should be the code of a combined horizontal and vertical reference.
            For example EPSG 7416 which refers to ETRS89/UTM zone 32 + DVR90''',
)

def usage():
    parser.print_help()

def create_pdal_pipeline(pargs, json_out, las_out):

    reader = {
        'type':'readers.las',
        'filename':'{0}'.format(pargs.las_file),
    }

    reproject = {
        "type": "filters.reprojection",
        "out_srs": "{0}".format(pargs.out_srs),
    }
    if pargs.in_srs:
        reproject['in_srs'] = "{0}".format(pargs.in_srs)

    writer = {
        'type': 'writers.las',
        'dataformat_id': 3,
        'minor_version': 3,
        'a_srs':'EPSG:{code}'.format(code=pargs.a_srs),
        'filename':'{0}'.format(las_out)
    }

    pipeline = []
    pipeline.append(reader)
    pipeline.append(reproject)
    pipeline.append(writer)

    with open(json_out, 'w') as fp:
        json.dump({'pipeline': pipeline}, fp, indent=4, separators=(',', ': '))


def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception as e:
        print(str(e))
        return 1

    kmname = constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" % (progname,kmname,time.asctime()))

    out_file = os.path.join(pargs.out_dir, os.path.basename(pargs.las_file))

    if not os.path.exists(pargs.out_dir):
        print pargs.out_dir
        os.makedirs(os.path.abspath(pargs.out_dir))

    # create pipeline
    pipeline = 'temp_{tile}.json'.format(tile=kmname)
    create_pdal_pipeline(pargs, pipeline, out_file, )

    # apply pipeline
    call = '{pdal_bin} pipeline {json_pipeline}'.format(pdal_bin=PDAL, json_pipeline=pipeline)
    subprocess.call(call)

    # clean up...
    os.remove(pipeline)
    return 0

if __name__ == '__main__':
    main(sys.argv)
