import sys,os,time
import zcheck_byg
from utils import redirect_output,names
import glob
def usage():
	print("Call:\n%s <las_files> <poly_base_dir> -use_local" %os.path.basename(sys.argv[0]))
	print("-use_local optional. Forces use of local db for reporting.")
	print("<poly_base_dir> is the root of a 'standard' directory of vector tiles clipped into 1km blocks")
	print("and grouped in 10 km subdirs (see definition in utils.names)")
	print("The <las_file> argument could be e.g. C:/abc/las/*.las")
	sys.exit()
	
def main(args):
	if len(args)<3:
		usage()
	progname=os.path.basename(args[0])
	logfile=open("%s.log" %progname,"w")
	redirect_output
	las_files=glob.glob(args[1])
	vector_root=args[2]
	stdout=redirect_output.redirect_stdout(logfile)
	stderr=redirect_output.redirect_stderr(logfile)
	sl="*-*"*23
	print(sl)
	print("Running %s at %s" %(progname,time.asctime()))
	print("%d input files from %s" %(len(las_files),args[1]))
	print(sl)
	done=0
	for fname in las_files:
		print(sl)
		print("Doing lasfile %s..." %fname)
		try:
			vector_tile=names.get_vector_tile(vector_root,fname)
		except ValueError,e:
			print(str(e))
			continue
		if not os.path.exists(vector_tile):
			print("Corresponding vector tile: %s does not exist!" %vector_tile)
			continue
		send_args=[progname,fname,vector_tile]
		if len(args)>3:
			send_args+=args[3:]
		zcheck_byg.main(send_args)
		done+=1
	print("Checked %d tiles, finished at %s" %(done,time.asctime()))
	#avoid writing to a closed fp...
	stdout.close()
	stderr.close()
	logfile.close()


if __name__=="__main__":
	main(sys.argv)
	