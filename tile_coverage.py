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
tile_coverage.py

Write a simple spatialite file with tile coverage geometries (tifs, las, etc..).
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import sys
import re
import argparse

from osgeo import ogr
from osgeo import osr

from qc import dhmqc_constants as constants

LOGGER = None

def log(text):
    """Print text to either logger or stdout."""
    if LOGGER is None:
        print(text)
    else:
        LOGGER.log(text)


class WalkFiles(object):
    """Walk only over all files below a path - return fullpath and mtime"""
    # pylint: disable=too-few-public-methods
    # Only one public method is needed in this case

    def __init__(self, path):
        self.walk_iter = os.walk(path)
        self.root, _, self.files = self.walk_iter.next()
        self.file_iter = iter(self.files)
        self.count = 0

    def __iter__(self):
        return self

    def next(self):
        """Return next """
        try:
            bname = self.file_iter.next()
        except StopIteration:
            self.count += 1
            self.root, _, self.files = self.walk_iter.next()
            while len(self.files) == 0:
                self.count += 1
                self.root, _, self.files = self.walk_iter.next()
            self.file_iter = iter(self.files)
            bname = self.file_iter.next()
        path = os.path.join(self.root, bname)

        return path, int(os.path.getmtime(path))

def connect_db(db_name, must_exist=False):
    """Create a connection to sqlite-database.

    Arguments:
        db_name:        File path to sqlite database
        must_exist:     coverage table must exists in database beforehand
    """

    layer = None
    driver = ogr.GetDriverByName('SQLite')
    datasource = driver.Open(db_name, 1)
    if datasource is not None:
        layer = datasource.GetLayerByName('coverage')
    else:
        datasource = driver.CreateDataSource(db_name, ['SPATIALITE=YES'])

    if must_exist:
        if layer is None:
            raise ValueError('The coverage table does not exist in {0}'.format(db_name))
    else:
        if layer is not None:
            raise ValueError('The coverage table is already created in {0}'.format(db_name))

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(constants.EPSG_CODE)
        layer = datasource.CreateLayer('coverage', srs, ogr.wkbPolygon, ['GEOMETRY_NAME=geom'])
        layer.CreateField(ogr.FieldDefn('tile_name', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('path', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('mtime', ogr.OFTInteger))
        layer.CreateField(ogr.FieldDefn('row', ogr.OFTInteger))
        layer.CreateField(ogr.FieldDefn('col', ogr.OFTInteger))
        layer.CreateField(ogr.FieldDefn('comment', ogr.OFTString))

    return datasource, layer

def update_db(datasource, layer):
    """Update timestamp of files."""

    n_updates = 0
    n_non_existing = 0
    n_done = 0

    for feature in layer:
        path = feature.GetFieldAsString(feature.GetFieldIndex('path'))
        mtime = feature.GetFieldAsInteger(feature.GetFieldIndex('mtime'))
        if not os.path.exists(path):
            n_non_existing += 1
            continue

        mtime_real = int(os.path.getmtime(path))
        if mtime_real > mtime:
            feature.SetField('mtime', mtime_real)
            n_updates += 1

        n_done += 1
        if n_done % 500 == 0:
            log("Done: {0:d}".format(n_done))

    log("Updated {0:d} rows.".format(n_updates))
    log("Encountered {0:d} non existing paths.".format(n_non_existing))

def remove_tiles(modify_datasource, deletion_datasource):
    """Remove tiles from a tile-coverage database.

    Arguments:
        modify_datasource:      tile-coverage OGR datasource that tiles are removed from.
        deletion_datasource:    tile-coverage lookup OGR datasource  with tiles we want to remove.
    """
    mod_layer = modify_datasource.GetLayerByName('coverage')
    del_layer = deletion_datasource.GetLayerByName('coverage')
    n_done = 0
    n_before = mod_layer.GetFeatureCount()

    for feature in del_layer:
        tile = feature.GetFieldAsString(feature.GetFieldIndex('tile_name'))

        if n_done % 500 == 0:
            print("Done: %d" % n_done)
        n_done += 1
        modify_datasource.ExecuteSQL("DELETE FROM coverage WHERE tile_name='{0}'".format(tile))

    n_removed = n_before - mod_layer.GetFeatureCount()
    print("Changes: %d" % n_removed)

def append_tiles(datasource, layer, walk_path, ext_match, wdepth=None,
                 rexclude=None, rinclude=None, rfpat=None, upsert=False):
    """Append tiles to a tile-coverage database."""
    n_insertions = 0
    n_excluded = 0
    n_badnames = 0
    n_dublets = 0
    print(walk_path)

    walker = WalkFiles(walk_path)

    for path, mtime in walker:
        # Walk of ALL 'files' below the toplevel folder.
        # Include and/or exclude some directory / filenames.
        # If you only need to index a subfolder point directly to that to increase
        # speed and avoid filename collisions.
        # Will include the FIRST tilename encountered,
        # subsequent similar tilenames will be excluded. Unless the --overwrite arg is used.

        root = os.path.dirname(path)
        name = os.path.basename(path)
        if root == walk_path:
            depth = 0
        else:
            depth = len(os.path.relpath(root, walk_path).split(os.path.sep))
        if wdepth is not None and wdepth < depth:
            continue
        if (rexclude is not None) and (re.search(rexclude, root)):
            n_excluded += 1
            continue
        if (rinclude is not None) and not re.search(rinclude, root):
            n_excluded += 1
            continue
        if rfpat is not None and not re.search(rfpat, name):
            n_excluded += 1
            continue

        ext = os.path.splitext(name)[1]
        if ext in ext_match:
            tile = constants.get_tilename(name)
            try:
                wkt = constants.tilename_to_extent(tile, return_wkt=True)
            except ValueError:
                n_badnames += 1
            else:
                row, col = constants.tilename_to_index(tile)
                geom = "GeomFromText('{0}', {1})".format(wkt, constants.EPSG_CODE)
                try:
                    if upsert:
                        insert = 'INSERT OR REPLACE'
                    else:
                        insert = 'INSERT'

                    sql = """{0} INTO
                               coverage (tile_name,
                                         path,
                                         mtime,
                                         row,
                                         col,
                                         GEOMETRY)
                             VALUES ('{1}','{2}','{3}',{4},{5},{6})"""
                    datasource.ExecuteSQL(sql.format(insert, tile, path, mtime, row, col, geom))


                except:
                    n_dublets += 1
                else:
                    n_insertions += 1
                    if n_insertions % 200 == 0:
                        log("Done: {0:d}".format(n_insertions))

    log("Inserted/updated {0:d} rows".format(n_insertions))

    if not upsert:
        log("Encountered {0:d} 'dublet' tilenames".format(n_dublets))

    if n_excluded > 0:
        log("Excluded {0:d} paths".format(n_excluded))

    log("Encountered {0:d} bad tile-names.".format(n_badnames))

def main(args):
    """Set up CLI and execute commands."""
    parser = argparse.ArgumentParser(description="Write/modify a sqlite file readable by " \
                                                 "e.g. ogr with tile coverage.")

    subparsers = parser.add_subparsers(help="Sub-command help", dest="mode")
    parser_create = subparsers.add_parser('create', help='Create tile coverage',
                                          description="Create a new tile coverage database")
    parser_create.add_argument("path", help="Path to directory to walk into")
    parser_create.add_argument("ext", help="Extension of relevant files")
    parser_create.add_argument("dbout", help="Name of output sqlite file.")
    parser_create.add_argument("--append", action="store_true",
                               help="Append to an already existing database.")
    parser_create.add_argument("--exclude", help="Regular expression of dirnames to exclude.")
    parser_create.add_argument("--include", help="Regular expression of dirnames to include.")
    parser_create.add_argument("--depth", type=int,
                               help="Max depth of subdirs to walk into (defaults to full depth)")
    parser_create.add_argument("--fpat", help="Regular expression of filenames to include.")
    parser_create.add_argument("--overwrite", action="store_true",
                               help="Overwrite record if tile already exists.")

    parser_update = subparsers.add_parser("update", help="Update timestamp of tiles",
                                          description="Update timestamp of existing tiles.")
    parser_update.add_argument("dbout", help="Path to existing database")

    parser_delete = subparsers.add_parser("remove", help="Remove tiles from one db which " \
                                                         "exist in another db")
    parser_delete.add_argument("db_to_modify", help="Path to database to be modified.")
    parser_delete.add_argument("db_tiles_to_delete",
                               help="Path to database containing tiles to remove.")

    pargs = parser.parse_args(args[1:])

    if pargs.mode == "create":
        db_name = pargs.dbout
        if not (pargs.append or pargs.overwrite):
            log("Creating coverage table.")
            datasource, layer = connect_db(db_name, False)
        else:
            datasource, layer = connect_db(db_name, True)
            log("Appending to/updating coverage table.")
        ext = pargs.ext
        if not ext.startswith("."):
            ext = "."+ext
        ext_match = [ext]
        walk_path = os.path.realpath(pargs.path)
        append_tiles(datasource, layer, walk_path, ext_match, pargs.depth, pargs.exclude,
                     pargs.include, pargs.fpat, pargs.overwrite)

    elif pargs.mode == "update":
        db_name = pargs.dbout
        log("Updating coverage table.")
        datasource, layer = connect_db(db_name, True)
        update_db(datasource, layer)

    elif pargs.mode == "remove":
        (datasource1, _) = connect_db(pargs.db_to_modify, True)
        (datasource2, _) = connect_db(pargs.db_tiles_to_delete, True)
        remove_tiles(datasource1, datasource2)

if __name__ == "__main__":
    main(sys.argv)
