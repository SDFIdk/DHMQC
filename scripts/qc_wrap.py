import sys,os,time
from multiprocessing import Process, Queue
from thatsDEM import report
from utils import redirect_output,names
import zcheck_road, zcheck_byg, classification_check
import glob
LOGDIR=os.path.join(os.path.dirname(__file__),"logs")
MAX_PROCESSES=4
def usage():
	print("Call:\n%s <test> <las_files> <vector_tile_root> -use_local" %os.path.basename(sys.argv[0]))
	print(" ")
	print("The <test> argument will decide which test to run, currently:")
	print("   zcheck_road or anything containing 'road': import zcheck_road")
	print("   zhceck_build or anything containing 'build': import zcheck_build / zcheck_byg")
	print("   classification_check or anything containing 'class': import classification check")
	print(" ")
	print("<vector_tile_root> is the root of a 'standard' directory of vector tiles clipped into 1km blocks,")
	print("and grouped in 10 km subdirs (see definition in utils.names)")
	print("This directory must contain vector tile of the appropriate geometry type for the chosen check.")
	print(" ")
	print("-use_local optional. Forces use of local db for reporting.")
	print(" ")
	print("The <las_file> argument could be e.g. C:/abc/las/*.las")
	print(" ")
	print("Additional arguments will be passed on to the selected test script...")
	sys.exit(1)

def run_check(p_number,testname,file_pairs,add_args):
	if testname=="z_roads":
		test_func=zcheck_road.main
	elif testname=="z_build":
		test_func=zcheck_byg.main
	elif testname=="classification":
		test_func=classification_check.main
	logname=testname+"_"+(time.asctime().split()[-2]).replace(":","_")+"_"+str(p_number)+".log"
	logname=os.path.join(LOGDIR,logname)
	logfile=open(logname,"w")
	stdout=redirect_output.redirect_stdout(logfile)
	stderr=redirect_output.redirect_stderr(logfile)
	sl="*-*"*23
	print(sl)
	print("Running %s rutine at %s, process: %d" %(testname,time.asctime(),p_number))
	print(sl)
	print("%d input file pairs" %len(file_pairs))
	done=0
	for lasname,vname  in file_pairs:
		print(sl)
		print("Doing lasfile %s..." %lasname)
		send_args=["",lasname,vname]+add_args
		test_func(send_args)
		done+=1
	print("Checked %d tiles, finished at %s" %(done,time.asctime()))
	#avoid writing to a closed fp...
	stdout.close()
	stderr.close()
	logfile.close()
		
def main(args):
	if len(args)<4:
		usage()
	if "-use_local" in args:
		#will do nothing if it already exists
		#should be done 'process safe' so that its available for writing for the child processes...
		report.create_local_datasource() 
	if len(args)>4:
		add_args=args[4:]
	else:
		add_args=[]
	# NOW for the magic conditional import of qc module
	testname=args[1]
	if "road" in testname:
		testname="z_roads"
	elif "build" in testname or "byg" in testname:
		testname="z_build"
	elif "class" in testname:
		testname="classification"
	else:
		print("%s not mathed to any test (yet....)")
		usage()
	las_files=glob.glob(args[2])
	vector_root=args[3]
	if not os.path.exists(vector_root):
		print("Sorry, %s does not exist" %vector_root)
		usage()
	t1=time.clock()
	print("Running qc_wrap at %s" %(time.asctime()))
	if not os.path.exists(LOGDIR):
		os.mkdir(LOGDIR)
	matched_files=[]
	for fname in las_files:
		try:
			vector_tile=names.get_vector_tile(vector_root,fname)
		except ValueError,e:
			print(str(e))
			continue
		if not os.path.exists(vector_tile):
			print("Corresponding vector tile: %s does not exist!" %vector_tile)
			continue
		matched_files.append((fname,vector_tile))
	print("%d las files matched with vector tiles." %len(matched_files))
	if len(matched_files)>0:
		n_tasks=max(min(int(len(matched_files)/2),MAX_PROCESSES),1)
		n_files_pr_task=int(len(matched_files)/n_tasks)
		print("Starting %d processes." %n_tasks)
		tasks=[]
		j=0
		for i in range(n_tasks):
			if (i<n_tasks-1):
				files_to_do=matched_files[j:j+n_files_pr_task]
			else:
				files_to_do=matched_files[j:]
			j+=n_files_pr_task
			p = Process(target=run_check, args=(i,testname,files_to_do,add_args,))
			tasks.append(p)
			p.start()
		for p in tasks:
			print("Joining...")
			p.join()
	t2=time.clock()
	print("Finished at %s" %(time.asctime()))
	print("Running time %.2f s" %(t2-t1))

if __name__=="__main__":
	main(sys.argv)