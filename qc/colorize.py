"""
Use PDAL pipeline to fill  RGB values in las/laz file from ortophoto downloaded from WMS.

Notes:


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

parser = ArgumentParser(description='Use PDAL pipeline to fill  RGB values in las/laz file from ortophoto downloaded from WMS', prog=progname)

parser.add_argument('las_file', help='Input las file')
parser.add_argument('out_dir', help='Output directory')
parser.add_argument('-wms_url', help='URL to WMS Capabilitites file')
parser.add_argument('-wms_layer', default='', help='Layer from WMS service')
parser.add_argument('-px_size', type=float, default=1.0, help='Pixel size of retrived WMS image')

def indent_xml(elem, level=0):
    """Reformats XML in order to print out nicely. Only useful for debugging...

       Taken from http://effbot.org/zone/element-lib.htm#prettyprint
    """

    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent_xml(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def create_pipeline(out_dir, las_file, tif_image, xml_file):
    """Creates a PDAL pipeline file that defines filters for colorizing las-files.

    With the use of a PDAL pipeline filter RGB values in a uncolored las file
    are colorized with RGB values from a tiff file. The filter is defined in
    a xml-file that can be used by pdal pipeline.

    Args:

    las_file          path to uncolored las-file
    tiff_image        path to tiff image
    xml_file          path to pipeline xml filter definition

    Example of XML filter definition:

    <?xml version="1.0" encoding="utf-8"?>
    <Pipeline version="1.0">
      <Writer type="writers.las">
        <Option name="filename">colorized.las</Option>
        <Filter type="filters.colorization">
          <Option name="dimensions">
            Red:1:1.0, Blue, Green::256.0
          </Option>
          <Option name="raster">aerial.tif</Option>
          <Reader type="readers.las">
            <Option name="filename">uncolored.las</Option>
          </Reader>
        </Filter>
      </Writer>
    </Pipeline>

    For more information see:
    http://www.pdal.io/stages/filters.colorization.html
    """

    out_dir = os.path.abspath(out_dir)
    las_file = os.path.abspath(las_file)

    # Create PDAL pileline xml-file
    pipeline = ET.Element('Pipeline', version='1.0')
    writer = ET.SubElement(pipeline, 'Writer', type='writers.las')
    ET.SubElement(writer, 'Option', name='filename').text = os.path.join(out_dir, os.path.basename(las_file))
    filter = ET.SubElement(writer, 'Filter', type='filters.colorization')
    ET.SubElement(filter, 'Option', name='raster').text = tif_image
    reader = ET.SubElement(filter, 'Reader', type='readers.las')
    ET.SubElement(reader, 'Option', name='filename').text = las_file

    indent_xml(pipeline)
    tree = ET.ElementTree(pipeline)
    tree.write(xml_file, 'UTF-8')


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
    xml_file = kmname + '.xml'

    if not os.path.exists(pargs.out_dir):
        print pargs.out_dir
        os.makedirs(os.path.abspath(pargs.out_dir))

    # Get image from WMS
    get_georef_image_wms(kmname, pargs.wms_url, pargs.wms_layer, tif_image, pargs.px_size)

    # PDAL pipeline
    create_pipeline(pargs.out_dir, pargs.las_file, tif_image, xml_file)
    call = ['pdal', 'pipeline', xml_file]
    subprocess.call(call)

    # clean up...
    os.remove(tif_image)
    os.remove(xml_file)

if __name__ == '__main__':
    main(sys.argv)
