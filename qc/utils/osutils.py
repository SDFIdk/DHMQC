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

###########################
## A class to redirect stdout and stderr and various other utils...
###########################

from __future__ import absolute_import
import sys
import os
import subprocess
import argparse

class ArgumentParser(argparse.ArgumentParser):
	def __init__(self, *args, **kwargs):
		argparse.ArgumentParser.__init__(self, *args, **kwargs)
	def error(self, message):
		self.print_usage(sys.stderr)
		if message:
			raise Exception(message)
		else:
			raise Exception("argument error...")


# Input arguments as a list - Popen will know what to do with it...
def run_command(args):
	prc = subprocess.Popen(args,  stdout = subprocess.PIPE,  stderr = subprocess.STDOUT, bufsize = -1)
	stdout, stderr = prc.communicate()
	return prc.poll(), stdout, stderr

class RedirectOutput(object):
	def __init__(self, fp = None, shut_up = True):
		self.fp = fp  # a filepointer - will NOT take ownership over this
		self.shut_up  = shut_up

	def __del__(self):
		self.close()

	def write(self, text):
		if self.fp is not None:
			self.fp.write(text)
		if not self.shut_up:
			sys.__stdout__.write(text)

	def close(self):
		self.fp = None

	def flush(self):
		if self.fp is not None:
			self.fp.flush()

	def set_be_quiet(self, be_quiet):
		self.shut_up = be_quiet

def redirect_stdout(fp = None, be_quiet = True):
	out = RedirectOutput(fp, be_quiet)
	sys.stdout = out
	return out

def redirect_stderr(fp = None, be_quiet = True):
	out = RedirectOutput(fp, be_quiet)
	sys.stderr = out
	return out

def reset_stdout():
	sys.stdout = sys.__stdout__

def reset_stderr():
	sys.stderr = sys.__stderr__
