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

import sys
import os
import platform
import shutil
import tempfile
import glob
import urllib2
import zipfile
import md5
import argparse
from cc import *
from core import *

import patch

HERE = os.getcwd()
ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
print(HERE, ROOT_DIR)

# output binaries and source input defined here
BIN_DIR = os.path.join(ROOT_DIR, "..", "qc", "thatsDEM", "lib")
if not os.path.exists(BIN_DIR):
    os.mkdir(BIN_DIR)

BUILD_DIR = os.path.join(ROOT_DIR, "build")

# path to pg_connection.py output file
PG_CONNECTION_FILE = os.path.join(ROOT_DIR, "..", "qc", "db", "pg_connection.py")

# triangle
LIB_TRI = "libtri"
DIR_TRI = os.path.join(ROOT_DIR, "triangle")
PATCH_TRIANGLE = os.path.join(ROOT_DIR, "triangle", "triangle_patch.diff")
URL_TRIANGLE = "http://www.netlib.org/voronoi/triangle.zip"
TRI_DEFINES = ["TRILIBRARY", "NO_TIMER"]
MD5_TRI = "Yjh\xfe\x94o)5\xcd\xff\xb1O\x1e$D\xc4"
DEF_TRI = os.path.join(BUILD_DIR, "libtri.def")

# spatial indexing
LIB_INDEX = "libtripy"
SRC_INDEX = [os.path.join(ROOT_DIR, "triangle", x) for x in ["_tri.c", "trig_index.c"]]
DEF_INDEX = os.path.join(BUILD_DIR, "libtripy.def")

# array geometry
LIB_GEOM = "libfgeom"
SRC_GEOM = [os.path.join(ROOT_DIR, "geometry", "array_geometry.c")]
DEF_GEOM = os.path.join(BUILD_DIR, "libfgeom.def")

# grid stuff
LIB_GRID = "libgrid"
SRC_GRID = [os.path.join(ROOT_DIR, "etc", "grid_stuff.c")]

class BuildObject(object):

    def __init__(self, name, outdir, source, include=[],
                 defines=[], link=[], def_file="", is_library=True):
        '''Initialize BuildObject.'''
        self.name = name
        self.source = source
        self.include = include
        self.defines = defines
        self.link = link  # a list of other build objects...
        self.def_file = def_file
        self.is_library = is_library  # else exe
        self.needs_rebuild = False
        if is_library:
            self.extension = DLL
        else:
            self.extension = EXE
        self.outname = os.path.join(outdir, self.name) + self.extension

    def _is_newer(self, p1, p2):
        '''Check which is newer, p1 or p2.'''

        if not os.path.exists(p1):
            return False
        if not os.path.exists(p2):
            return True
        return os.path.getmtime(p1) > os.path.getmtime(p2)

    def set_needs_rebuild(self, dep_files=[]):
        '''just set this var in the dependency order of mutually dependent builds...'''

        self.needs_rebuild = False
        for s in self.source + [self.def_file] + dep_files:
            if self._is_newer(s, self.outname):
                self.needs_rebuild = True
                return

        for n in self.link:
            if isinstance(n, BuildObject) and n.needs_rebuild:
                self.needs_rebuild = True
                return


def patch_triangle():
    '''Patch the Triangle source with 64-bit modification.'''

    print("Starting patching process of triangle")
    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)

    print("Downloading triangle")
    try:
        with open("triangle.zip", 'wb') as f:
            response = urllib2.urlopen(URL_TRIANGLE)
            assert(response.getcode() == 200)
            f.write(response.read())

        print("Done")

        zf = zipfile.ZipFile("triangle.zip")
        zf.extract("triangle.c")
        zf.extract("triangle.h")

        print("Checking md5 sum of downloaded file")
        with open("triangle.c", "rb") as f:
            m5 = md5.new(f.read()).digest()

        zf.close()
        assert(m5 == MD5_TRI)

        rc = patch.fromfile(PATCH_TRIANGLE)
        rc.apply()
        SRC_TRI = os.path.join(tmpdir, "triangle.c")
    except Exception, e:
        print("Patching process failed with error:\n" + str(e))
        rc = False
    else:
        OLIB_TRI.source = [SRC_TRI]
        OLIB_INDEX.include.append(tmpdir)

    os.chdir(HERE)
    return rc, tmpdir  # tmpdir should be deleted after a build...


def cleanup(tmpdir):
    '''Clean up when things go wrong.'''

    if tmpdir is None or (not os.path.exists(tmpdir)):
        return
    try:
        shutil.rmtree(tmpdir)
    except Exception, e:
        print("Failed to delete temporary directory: " + tmpdir + "\n" + str(e))

# and now REALLY specify what to build
OLIB_TRI = BuildObject(LIB_TRI, BIN_DIR, [], defines=TRI_DEFINES, def_file=DEF_TRI)
OLIB_INDEX = BuildObject(LIB_INDEX, BIN_DIR, SRC_INDEX, link=[OLIB_TRI], def_file=DEF_INDEX)
OLIB_GEOM = BuildObject(LIB_GEOM, BIN_DIR, SRC_GEOM, def_file=DEF_GEOM)
OLIB_GRID = BuildObject(LIB_GRID, BIN_DIR, SRC_GRID)


# Additional args which are not compiler selection args:
ARGS = {"-PG": {"help": "Specify PostGis connection if you want to use a PG-db for reporting."},
        "-debug": {"help": "Do a debug build.", "action": "store_true"},
        "-force": {"help": "Force a full rebuild.", "action": "store_true"},
        "-v": {"help": "Be verbose.", "action": "store_true"},
        }


def main(args):
    descr = "Build and setup script for dhmqc repository. Will by default try to build with gcc."
    parser = argparse.ArgumentParser(description=descr)
    ARGS.update(COMPILER_SELECTION_OPTS)
    for key in ARGS:
        parser.add_argument(key, **ARGS[key])

    # some of the ARGS are not compiler selection args, but can be safely
    # passed on to select_compiler which only checks for the relevant
    # ones...
    pargs = parser.parse_args(args[1:])

    compiler = select_compiler(args[1:])
    print("Selecting compiler: %s" % compiler)
    build_dir = os.path.realpath("./BUILD")

    OLIB_TRI.set_needs_rebuild([PATCH_TRIANGLE])
    OLIB_TRI.needs_rebuild |= pargs.force
    OLIB_INDEX.set_needs_rebuild()
    OLIB_INDEX.needs_rebuild |= pargs.force
    tmpdir = None  # a diretory we need to remove

    if OLIB_TRI.needs_rebuild or OLIB_INDEX.needs_rebuild:
        # libindex needs triangle.h
        ok, tmpdir = patch_triangle()
        if not ok:
            print("Unable to patch triangle..Aborting...")
            cleanup(tmpdir)
            sys.exit(1)

    if pargs.x64:
        # set our 64-bit patch define
        OLIB_TRI.defines.append("POINTERS_ARE_VERY_LONG")
    elif "64" in platform.architecture()[0]:
        print("WARNING: you're running 64-bit python but haven't specified a 64-bit build ( -x64 ) !")
    if IS_WINDOWS:
        if compiler.IS_MSVC:
            # another define which should (probably) be set for MSVC-compilers
            OLIB_TRI.defines.append("CPU86")
        else:
            pass

    # stuff thats autonomic
    for out in [OLIB_GEOM, OLIB_GRID]:
        out.set_needs_rebuild()
        out.needs_rebuild |= pargs.force

    is_debug = pargs.debug
    is_verbose = pargs.v
    sl = "*" * 50

    for out in [OLIB_TRI, OLIB_INDEX, OLIB_GEOM, OLIB_GRID]:
        if not out.needs_rebuild:
            print("%s\n%s does not need a rebuild. Use -force to force a rebuild.\n%s" %
                  (sl, out.name, sl))
            continue

        print("%s\nBuilding: %s\n%s" % (sl, out.name, sl))
        link = [x.outname for x in out.link]

        try:
            ok = build(compiler, out.outname, out.source, out.include, out.defines, is_debug,
                       out.is_library, link, out.def_file, build_dir=build_dir, link_all=False,
                       verbose=is_verbose)

        except Exception, e:
            print("Error: " + str(e) + "\n")
            print("*** MOST LIKELY the selected compiler is not available in the current environment.")
            print("*** You can overrider the auto-selected compiler command " +
                  compiler.COMPILER + " with the -cc option.")
            cleanup(tmpdir)
            sys.exit(1)

        print("Succes: %s" % ok)
        if not ok:
            cleanup(tmpdir)
            sys.exit(1)


    if pargs.PG is not None:
        print("Writing pg-connection to " + PG_CONNECTION_FILE)
        with open(PG_CONNECTION_FILE, "w") as f:
            f.write('PG_CONNECTION="PG: ' + pargs.PG + '"' + '\n')


if __name__ == "__main__":
    main(sys.argv)
