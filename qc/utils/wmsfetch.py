""" wmsfect.py - Fetch ortophoto from Kortforsyningen WMS

usage: wmsfetch.py [-h] [--pxsize PXSIZE] [--timeout TIMEOUT] [-v]
                   tilename [out]

Download PNG image from Kortforsyningen WMS

positional arguments:
  tilename
  out

optional arguments:
  -h, --help         show this help message and exit
  --pxsize PXSIZE
  --timeout TIMEOUT
  -v, --verbose

Example:

        > python wmsfetch.py -v --pxsize 2 wmsfetch 6173_727 ortophoto.tiff

          Downloading from WMS. It might take a while...

          Bounding box of tile: (727000, 6173000, 728000, 6174000)
          Image size: (500, 500)

"""
import os
import time
import argparse
import tempfile
from osgeo import gdal, osr

import owslib
from owslib.wms import WebMapService

from urllib import urlencode
from owslib.util import openURL
from owslib.wms import ServiceIdentification, ContentMetadata
from owslib.wms import ServiceProvider, OperationMetadata

class WebMapServiceTimeOut(WebMapService):
    """WebMapService with a timeout setting that can be changed by the user.

    The class works by overriding a few key functions from the parent class.
    Overridden functions are based on owslib version 0.8.8. In newer versions
    of owslib a timeout can be specified, unfortunately it is not yet a part
    of the OSGeo4W suite. Once it is, this hack can be removed.

    """
    def __init__(self, url, version='1.1.1', xml=None, username=None,
                 password=None, parse_remote_metadata=False, timeout=240):
        self.timeout = timeout
        super(WebMapServiceTimeOut, self).__init__(url, version=version, xml=xml,
              username=username, password=password, parse_remote_metadata=parse_remote_metadata)


    def _buildMetadata(self, parse_remote_metadata=False):
        """ Overriding function owslib.wms.WebMapService._buildMetadata. The functionality is
        completely unchanged, except for a longer default timeout when fetching stuff
        from the internet.
        Modified from owslib v. 0.8.8"""

        #serviceIdentification metadata
        serviceelem=self._capabilities.find('Service')
        self.identification=ServiceIdentification(serviceelem, self.version)

        #serviceProvider metadata
        self.provider=ServiceProvider(serviceelem)

        #serviceOperations metadata
        self.operations=[]
        for elem in self._capabilities.find('Capability/Request')[:]:
            self.operations.append(OperationMetadata(elem))

        #serviceContents metadata: our assumption is that services use a top-level
        #layer as a metadata organizer, nothing more.
        self.contents={}
        caps = self._capabilities.find('Capability')

        #recursively gather content metadata for all layer elements.
        #To the WebMapService.contents store only metadata of named layers.
        def gather_layers(parent_elem, parent_metadata):
            for index, elem in enumerate(parent_elem.findall('Layer')):
                cm = ContentMetadata(elem, parent=parent_metadata, index=index+1,
                        # Using time from self instead of the default timeout as
                        # originally specified in owslib.
                        parse_remote_metadata=parse_remote_metadata, timeout=self.timeout)
                if cm.id:
                    if cm.id in self.contents:
                        warnings.warn('Content metadata for layer "%s" already exists. Using child layer' % cm.id)
                    self.contents[cm.id] = cm
                gather_layers(elem, cm)
        gather_layers(caps, None)

        #exceptions
        self.exceptions = [f.text for f \
                in self._capabilities.findall('Capability/Exception/Format')]

    def getmap(self, layers=None, styles=None, srs=None, bbox=None,
               format=None, size=None, time=None, transparent=False,
               bgcolor='#FFFFFF',
               exceptions='application/vnd.ogc.se_xml',
               method='Get',
               **kwargs
               ):
        """ Overriding function owslib.wms.WebMapService.getmap. The functionality is
        completely unchanged, except for a longer default timeout when fetching stuff
        from the internet.
        Modified from owslib v. 0.8.8"""
        try:
            base_url = next((m.get('url') for m in self.getOperationByName('GetMap').methods if m.get('type').lower() == method.lower()))
        except StopIteration:
            base_url = self.url
        request = {'version': self.version, 'request': 'GetMap'}

        # check layers and styles
        assert len(layers) > 0
        request['layers'] = ','.join(layers)
        if styles:
            assert len(styles) == len(layers)
            request['styles'] = ','.join(styles)
        else:
            request['styles'] = ''

        # size
        request['width'] = str(size[0])
        request['height'] = str(size[1])

        request['srs'] = str(srs)
        request['bbox'] = ','.join([repr(x) for x in bbox])
        request['format'] = str(format)
        request['transparent'] = str(transparent).upper()
        request['bgcolor'] = '0x' + bgcolor[1:7]
        request['exceptions'] = str(exceptions)

        if time is not None:
            request['time'] = str(time)

        if kwargs:
            for kw in kwargs:
                request[kw]=kwargs[kw]

        data = urlencode(request)

        # timeout argument added here. Using value from self.
        u = openURL(base_url, data, method, username = self.username,
                    password = self.password, timeout=self.timeout)

        # check for service exceptions, and return
        if u.info()['Content-Type'] == 'application/vnd.ogc.se_xml':
            se_xml = u.read()
            se_tree = etree.fromstring(se_xml)
            err_message = unicode(se_tree.find('ServiceException').text).strip()
            raise ServiceException(err_message, se_xml)
        return u

def parse_tilename(tilename):
    # should use function from dhmqc_contants...
    S = tilename.split('_')[1:3]
    N = int(S[0])*1000
    E = int(S[1])*1000

    return (N, E)

def download_image(tilename, url, layer, outputfile=None, px_size=0.1, timeout=500, verbose=False):

    t0 = time.time()

    (N, E) = parse_tilename(tilename)

    bb = (E, N, E+1000, N+1000)

    size_x = int((bb[2]-bb[0]) / px_size)
    size_y = int((bb[3]-bb[1]) / px_size)

    if verbose:
        print('Downloading %s. It might take a while...' % outputfile)
        print(' ')
        print('Bounding box of tile: %s' % str(bb))
        print('Image size: (%s, %s)' % (size_x, size_y))

    ows_version = [int(n) for n in owslib.__version__.split('.')]
    if ows_version[0] >= 0 and ows_version[1] >= 9:
        wms = WebMapService(url, timeout=timeout)
    else:
        # use stupid method override hack
        wms = WebMapServiceTimeOut(url, timeout=timeout)

    img = wms.getmap(layers=[layer], styles=[''], srs='EPSG:25832',
                     bbox=bb, size=(size_x, size_y), format=r'image/jpeg')

    out = open(outputfile, 'wb')
    out.write(img.read())
    out.close()

    t1 = time.time()

    if verbose:
        print('Download took %s s' % str(t1-t0))

    return outputfile

def georef_image(tilename, src_file, dst_file, px_size=0, verbose=False):
    t0 = time.time()

    if not dst_file:
        dst_file = tilename + '.tiff'

    src_ds = gdal.Open(src_file)
    driver = gdal.GetDriverByName('GTiff')

    dst_ds = driver.CreateCopy(dst_file, src_ds, 0, ['TILED=YES'])

    (N, E) = parse_tilename(tilename)

    gt = (E, px_size, 0, N+1000, 0, -px_size)

    dst_ds.SetGeoTransform(gt)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(25832)
    dst_wkt = srs.ExportToWkt()

    dst_ds.SetProjection(dst_wkt)

    dst_ds = None
    src_ds = None

    t1 = time.time()
    if verbose:
        print('Georeferencing took %s s' % str(t1-t0))

def get_georef_image_wms(tilename, wms_url, wms_layer, tiff_image, px_size, timeout=500, verbose=False):
    png_file = download_image(tilename, wms_url, wms_layer, 'temp.png', px_size, timeout=timeout, verbose=verbose)
    georef_image(tilename, png_file, tiff_image, px_size, verbose=verbose)
    os.remove(png_file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download PNG image from Kortforsyningen WMS')

    parser.add_argument('tilename', action='store')
    parser.add_argument('out', action='store', nargs='?', default=None)
    parser.add_argument('--pxsize', action='store', default=0.1, type=float)
    parser.add_argument('--timeout', action='store', default=500, type=int)
    parser.add_argument('-v', '--verbose', action='store_true', default=False)

    args = parser.parse_args()
    get_georef_image_wms(args.tilename, args.out, args.pxsize, timeout=args.timeout, verbose=args.verbose)
