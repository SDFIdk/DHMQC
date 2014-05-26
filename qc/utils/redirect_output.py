###########################
## A class to redirect stdout and stderr
###########################
import sys,os

class RedirectOutput(object):
	def __init__(self,fp=None,shut_up=True):
		self.fp=fp  # a filepointer - will NOT take owenership over this
		self.shut_up=shut_up
	def __del__(self):
		self.close()
	def write(self,text):
		if self.fp is not None:
			self.fp.write(text)
		if not self.shut_up:
			sys.__stdout__.write(text)
	def close(self):
		self.fp=None
	def flush(self):
		if self.fp is not None:
			self.fp.flush()

def redirect_stdout(fp=None):
	out=RedirectOutput(fp)
	sys.stdout=out
	return out

def redirect_stderr(fp=None):
	out=RedirectOutput(fp)
	sys.stderr=out
	return out

def reset_stdout():
	sys.stdout=sys.__stdout__

def reset_stderr():
	sys.stderr=sys.__stderr__
