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

from pyspatialite import dbapi2 as spatialite
from qc import dhmqc_constants as constants

try:
    import boto3
except ImportError:
    HAS_BOTO = False #s3 not available
else:
    HAS_BOTO = True

INIT_DB = """SELECT InitSpatialMetadata(1)"""

CREATE_DB = """CREATE TABLE coverage(tile_name TEXT unique,
                                     path TEXT,
                                     mtime INTEGER,
                                     row INTEGER,
                                     col INTEGER,
                                     comment TEXT)"""

ADD_GEOMETRY = """SELECT AddGeometryColumn('coverage',
                                           'geom',
                                           {epsg},
                                           'POLYGON',
                                           'XY')""".format(epsg=constants.EPSG_CODE)

LOGGER = None

def log(text):
    """Print text to either logger or stdout."""
    if LOGGER is None:
        print(text)
    else:
        LOGGER.log(text)


class WalkFiles(object):
    """Walk only over all files below a path - return fullpath and mtime"""

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

class WalkBucket(object):
    """Can walk over keys in a S3 bucket - return fullpath and mtime"""

    def __init__(self, path):
        path = path.replace("s3://", "")
        if path.endswith("/"):
            #make sure the path does not end with a /
            path = path[:-1]
        #see if we wanna look into a 'subfolder'
        i = path.find("/")
        if i != -1:
            bucket_name = path[:i]
            bucket_prefix = path[i+1:]
        else:
            bucket_name = path
            bucket_prefix = None
        s3_resource = boto3.resource("s3")
        self.bucket = s3_resource.Bucket(bucket_name)
        if bucket_prefix is None:
            self.bucket_iter = iter(self.bucket.objects.all())
        else:
            #we only want 'subdirs' that exactly match the prefix! So append a /
            if not bucket_prefix.endswith("/"):
                bucket_prefix += "/"
            self.bucket_iter = iter(self.bucket.objects.filter(Prefix=bucket_prefix))
        self.root = "s3://" + bucket_name + "/"

    def __iter__(self):
        return self

    def next(self):
        """Return next object."""
        obj = self.bucket_iter.next()
        key = obj.key
        return self.root+key, 0  #TODO - get modification time.


def connect_db(db_name, must_exist=False):
    """Create a connection to sqlite-database.

    Arguments:
        db_name:        File path to sqlite database
        must_exist:     coverage table must exists in database beforehand
    """

    try:
        con = spatialite.connect(db_name)
        cur = con.cursor()
    except spatialite.Error, msg:
        log("Unable to connect to "+db_name)
        log(str(msg))
        raise ValueError("Invalid sqlite db.")

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coverage'")
    tables = cur.fetchone()
    exists = tables is not None and (len(tables) == 1)

    if must_exist:
        if not exists:
            raise ValueError("The coverage table does not exist in " + db_name)
    else:
        if exists:
            raise ValueError("The coverage table is already created in " + db_name)
        cur.execute(INIT_DB)
        cur.execute(CREATE_DB)
        cur.execute(ADD_GEOMETRY)
        con.commit()

    return con, cur

def update_db(con, cur):
    """Update timestamp of files."""

    n_updates = 0
    n_non_existing = 0
    n_done = 0
    cur.execute("SELECT rowid, path, mtime FROM coverage")
    data = cur.fetchall()
    for row in data:
        row_id = int(row[0])
        path = row[1]
        mtime = int(row[2])
        if not os.path.exists(path):
            n_non_existing += 1
            continue

        mtime_real = int(os.path.getmtime(path))
        if mtime_real > mtime: #does this make sense, updating the existing iteration?
            cur.execute("UPDATE coverage SET mtime=? WHERE rowid=?", (mtime, row_id))
            con.commit()
            n_updates += 1

        n_done += 1
        if n_done % 500 == 0:
            log("Done: {0:d}".format(n_done))

    log("Updated {0:d} rows.".format(n_updates))
    log("Encountered {0:d} non existing paths.".format(n_non_existing))

def remove_tiles(modify_con, deletion_con):
    """Remove tiles from a tile-coverage database.

    Arguments:
        modify_con:     tile-coverage database that tiles are removed from.
        deletion_con:   tile-coverage lookup database with tiles we want to remove.
    """
    deletion_cur = deletion_con.cursor()
    modify_cur = modify_con.cursor()
    deletion_cur.execute("SELECT tile_name FROM coverage")
    tiles = deletion_cur.fetchall()
    n_done = 0
    for row in tiles:
        tile = row[0]
        if n_done % 500 == 0:
            print("Done: %d" % n_done)
        n_done += 1
        modify_cur.execute("DELETE FROM coverage WHERE tile_name=?", (tile, ))
    modify_con.commit()
    n_removed = modify_con.total_changes
    print("Changes: %d" % n_removed)

def append_tiles(con, cur, walk_path, ext_match, wdepth=None,
                 rexclude=None, rinclude=None, rfpat=None, upsert=False):
    """Append tiles to a tile-coverage database."""
    n_insertions = 0
    n_excluded = 0
    n_badnames = 0
    n_dublets = 0
    is_s3 = walk_path.startswith("s3://")
    print(walk_path)

    if is_s3:
        if not HAS_BOTO:
            raise Exception("boto3 is needed to read files from s3!")
        walker = WalkBucket(walk_path)
    else:
        walker = WalkFiles(walk_path)

    for path, mtime in walker:
        # Walk of ALL 'files' below the toplevel folder -
        # this behaviour is needed to comply with S3 which is really a key/value store.
        # Inlcude and /or exclude some directory / filenames.
        # If you only need to index a subfolder -
        # point directly to that to increase speed and avoid filename collisions
        # Will include the FIRST tilename encountered.
        # Subsequent similar tilenames will be excluded - unless the --overwrite arg is used.

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
                        sql = """INSERT OR REPLACE INTO
                                   coverage (tile_name,
                                             path,
                                             mtime,
                                             row,
                                             col,
                                             geom)
                                 VALUES ('{0}','{1}','{2}',{3},{4},{5})""".format(tile,
                                                                                  path,
                                                                                  mtime,
                                                                                  row,
                                                                                  col,
                                                                                  geom)
                        cur.execute(sql)
                    else:
                        sql = """INSERT OR REPLACE INTO
                                   coverage (tile_name,
                                             path,
                                             mtime,
                                             row,
                                             col,
                                             geom)
                                 VALUES ('{0}','{1}','{2}',{3},{4},{5})""".format(tile,
                                                                                  path,
                                                                                  mtime,
                                                                                  row,
                                                                                  col,
                                                                                  geom)
                        cur.execute(sql)

                except spatialite.Error:
                    n_dublets += 1
                else:
                    n_insertions += 1
                    if n_insertions % 200 == 0:
                        log("Done: {0:d}".format(n_insertions))
                    con.commit()

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

    subparsers = parser.add_subparsers(help="sub-command help", dest="mode")
    parser_create = subparsers.add_parser('create', help='create help',
                                          description="create a new database")
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

    parser_update = subparsers.add_parser("update", help="Update timestamp of tiles.",
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
            con, cur = connect_db(db_name, False)
        else:
            con, cur = connect_db(db_name, True)
            log("Appending to/updating coverage table.")
        ext = pargs.ext
        if not ext.startswith("."):
            ext = "."+ext
        ext_match = [ext]
        walk_path = pargs.path
        if not walk_path.startswith("s3://"):
            walk_path = os.path.realpath(walk_path)
        append_tiles(con, cur, walk_path, ext_match, pargs.depth, pargs.exclude,
                     pargs.include, pargs.fpat, pargs.overwrite)
        cur.close()
        con.close()

    elif pargs.mode == "update":
        db_name = pargs.dbout
        log("Updating coverage table.")
        con, cur = connect_db(db_name, True)
        update_db(con, cur)
        cur.close()
        con.close()

    elif pargs.mode == "remove":
        (con1, _) = connect_db(pargs.db_to_modify, True)
        (con2, _) = connect_db(pargs.db_tiles_to_delete, True)
        remove_tiles(con1, con2)
        con1.close()
        con2.close()
    else:
        raise Exception("Unknown mode: " + pargs.mode)
    return 0

if __name__ == "__main__":
    main(sys.argv)
