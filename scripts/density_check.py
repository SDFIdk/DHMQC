import os,sys
import time
import subprocess
from thatsDEM.report import report_density
from utils.names import get_1km_name
#-b decimin signals that returnval is min_density*10, -p
PAGE_ARGS=[os.path.join("lib","page"),"-F","Rlast","-p","boxdensity:50","-b","decimin"]
PAGE_GRID_FRMT="G/{0:.2f}/{1:.2f}/10/10/100/-9999"
CELL_SIZE=100  #100 m cellsize in density-grid
#input arguments as a list.... Popen will know what to do with it....
def run_command(args):
	prc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
	stdout,stderr=prc.communicate()
	return prc.poll(),stdout,stderr


def usage():
	print("Simple wrapper of 'page'")
	print("To run:")
	print("%s <las_tile> <output_file>  (options - none yet...)" %(os.path.basename(sys.argv[0])))
	sys.exit()

def main(args):
	if len(args)<3:
		usage()
	print("Running %s (a wrapper of 'page') at %s" %(os.path.basename(args[0]),time.asctime()))
	lasname=args[1]
	outname=args[2]
	kmname=get_1km_name(lasname)
	try:
		N,E=kmname.split("_")[1:]
		N=int(N)
		E=int(E)
	except Exception,e:
		print("Exception: %s" %str(e))
		print("Bad 1km formatting of las file: %s" %lasname)
		return 1
	xllcorner=E*1e3+0.5*CELL_SIZE
	yllcorner=N*1e3+0.5*CELL_SIZE
	grid_params=PAGE_GRID_FRMT.format(yllcorner,xllcorner)
	page_args=PAGE_ARGS+["-o",outname,"-g",grid_params,lasname]
	rc,stdout,stderr=run_command(page_args)
	ret=0
	if stdout is not None:
		print(stdout)
	if stderr is not None:
		print(stderr)
		#something went wrong... use that...
		rc=-2
		ret=1
	else:	
		if rc<0:
			rc=-1 #this means that we probably have no-data everywhere...
		else:
			den=rc/10.0
	report_density(kmname,den,outname)
	return ret
	


if __name__=="__main__":
	main(sys.argv)