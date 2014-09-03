###########################
## A class to redirect stdout and stderr and various other utils...
###########################
import sys,os, subprocess,argparse

class ArgumentParser(argparse.ArgumentParser):
	def __init__(self,*args,**kwargs):
		argparse.ArgumentParser.__init__(self,*args,**kwargs)
	def error(self,message):
		self.print_usage(sys.stderr)
		if message:
			raise Exception(message)
		else:
			raise Exception("argument error...")
		

#input arguments as a list.... Popen will know what to do with it....
def run_command(args):
	prc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
	stdout,stderr=prc.communicate()
	return prc.poll(),stdout,stderr

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
	def set_be_quiet(self,be_quiet):
		self.shut_up=be_quiet

def redirect_stdout(fp=None, be_quiet=True):
	out=RedirectOutput(fp, be_quiet)
	sys.stdout=out
	return out

def redirect_stderr(fp=None, be_quiet=True):
	out=RedirectOutput(fp, be_quiet)
	sys.stderr=out
	return out

def reset_stdout():
	sys.stdout=sys.__stdout__

def reset_stderr():
	sys.stderr=sys.__stderr__
