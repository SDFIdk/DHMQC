# Copyright (c) 2015, Danish Geodata Agency <gst@gst.dk>
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

import sys
import os
import time
import subprocess

# Import some relevant modules...
import dhmqc_constants as constants

# If you want this script to be included in the test-suite use this subclass.
# Otherwise argparse.ArgumentParser will be the best choice :-)
from utils.osutils import ArgumentParser



# To always get the proper name in usage / help - even when called from a wrapper...
progname = os.path.basename(__file__).replace(".pyc", ".py")

# Argument handling - if module has a parser attributte it will be used to check
# arguments in wrapper script.

# A simple subclass of argparse, ArgumentParser which raises an exception instead
# of using sys.exit if supplied with bad arguments...
parser = ArgumentParser(description = "Compress las to laz files using an sqlite index", prog = progname)

# Add some arguments below
parser.add_argument("las_file",  help = "input 1km las tile.")
parser.add_argument("out_dir",   help = "Output directory (root) for laz file.")


# A usage function will be imported by wrapper to print usage for test
# otherwise ArgumentParser will handle that...
def usage():
	parser.print_help()


def main(args):
	try:
		pargs = parser.parse_args(args[1:])
	except Exception,e:
		print(str(e))
		return 1
	kmname = constants.get_tilename(pargs.las_file)
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	if not os.path.exists(pargs.out_dir):
		os.mkdir(pargs.out_dir)
	outpath = os.path.join(pargs.out_dir,kmname + '.laz')

    # Consider using laszip-cli here (probably not - change slash/sspplash instead)
	rc = subprocess.call('laszip -i ' + pargs.las_file + ' -o ' + outpath)
	assert rc == 0


# To be able to call the script 'stand alone'
if __name__=="__main__":
	main(sys.argv)
