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
#
# UPDATE: We now include helios as an external dependency - so we keep a
# local helios repo at a specific revision here.
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

HERE = os.getcwd()
ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))

# output binaries and source input defined here
QC_DIR = os.path.join(ROOT_DIR, "..", "qc")

THATSDEM_URL = "https://bitbucket.org/kevers/thatsdem"
THATSDEM_REPO = os.path.join(QC_DIR, "thatsDEM")
THATSDEM_REV = "default"

# path to pg_connection.py output file
PG_CONNECTION_FILE = os.path.join(ROOT_DIR, "..", "qc", "db", "pg_connection.py")


def is_newer(p1, p2):
    if not os.path.exists(p1):
        return False
    if not os.path.exists(p2):
        return True
    return os.path.getmtime(p1) > os.path.getmtime(p2)


class BuildObject(object):

    def __init__(self, name, outdir, source, include=[],
                 defines=[], link=[], def_file="", is_library=True):
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

    def set_needs_rebuild(self, dep_files=[]):
        # just set this var in the dependency order of mutually dependent
        # builds...
        self.needs_rebuild = False
        for s in self.source + [self.def_file] + dep_files:
            if is_newer(s, self.outname):
                self.needs_rebuild = True
                return
        for n in self.link:
            if isinstance(n, BuildObject) and n.needs_rebuild:
                self.needs_rebuild = True
                return

def update_thatsDEM(args):
    print("Making sure that external dependency thatsDEM is up to date.")
    os.chdir(QC_DIR)
    if not os.path.exists(THATSDEM_REPO):
        print("thatsDEM repo does not exist - cloning it.")
        try:
            rc, msg = run_cmd(["hg", "clone", THATSDEM_URL, THATSDEM_REPO])
            assert(rc == 0)
        except Exception as e:
            print("An exception orccured: " + str(e))
            return 1
    os.chdir(THATSDEM_REPO)
    try:
        rc, msg = run_cmd(["hg", "pull", THATSDEM_URL])
        assert(rc == 0)
        rc, msg = run_cmd(["hg", "update", THATSDEM_REV])
        print rc
        assert(rc == 0)
    except Exception as e:
        print("An exception occured: " + str(e))
        return 1
    os.chdir(os.path.join(THATSDEM_REPO, "src", "build"))
    try:
        # build thatsDEM package. Making sure to pass wanted build arguments.
        args.insert(0, 'python')
        args.insert(1, 'build.py')
        rc, msg = run_cmd(args)
    except Exception as e:
        print("Building thatsDEM failed: " + str(e))
        return 1
    os.chdir(HERE)
    return 0

# Additional args which are not compiler selection args:
ARGS = {"-PG": {"help": "Specify PostGis connection if you want to use a PG-db for reporting."},
        "-debug": {"help": "Do a debug build.", "action": "store_true"},
        "-force": {"help": "Force a full rebuild.", "action": "store_true"}
        }


def main(args):
    descr = "Build and setup script for dhmqc repository. Will be default try to build with gcc."
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

    # update thatsDEM
    rc = update_thatsDEM(args[1:])
    assert(rc == 0)

    is_debug = pargs.debug
    sl = "*" * 50

    if pargs.PG is not None:
        print("Writing pg-connection to " + PG_CONNECTION_FILE)
        with open(PG_CONNECTION_FILE, "w") as f:
            f.write('PG_CONNECTION="PG: ' + pargs.PG + '"' + '\n')


if __name__ == "__main__":
    main(sys.argv)
