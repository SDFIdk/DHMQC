import subprocess
import xml.etree.ElementTree as ET
from utils.wmsfetch import get_georef_image_wms

"""
Use PDAL pipeline to fill  RGB values in las/laz file from ortophoto downloaded from WMS.

Notes:

http://www.pdal.io/stages/filters.colorization.html

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

"""

# Reformats XML in order to print out nicely. Only useful for debugging...
# Taken from http://effbot.org/zone/element-lib.htm#prettyprint
def indent_xml(elem, level=0):
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

# First steps. Very hardcoded test-files.
tilename = '6173_727'

tiff_image = tilename + '.tiff'
xml_file = tilename + '.xml'
las_uncolored = '/Users/kevers/gis/DHM/PC/617_72/1km_6173_727.laz'
las_colored = tilename + '_colored.laz'

# Create PDAL pileline xml-file
pipeline = ET.Element('Pipeline', version='1.0')
writer = ET.SubElement(pipeline, 'Writer', type='writers.las')
ET.SubElement(writer, 'Option', name='filename').text = las_colored
filter = ET.SubElement(writer, 'Filter', type='filters.colorization')
ET.SubElement(filter, 'Option', name='raster').text = tiff_image
reader = ET.SubElement(filter, 'Reader', type='readers.las')
ET.SubElement(reader, 'Option', name='filename').text = las_uncolored

indent_xml(pipeline)
tree = ET.ElementTree(pipeline)
tree.write(xml_file, 'UTF-8')

# Get image from WMS
#get_georef_image_wms(tilename, tiff_image, 0.5)

# PDAL pipeline
call = ['pdal', 'pipeline', xml_file]
subprocess.call(call)

