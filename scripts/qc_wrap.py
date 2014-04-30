import sys,os,time
from multiprocessing import Process, Queue
from thatsDEM import report
from utils import redirect_output,names
import z_precision_roads, z_precision_buildings, classification_check, count_classes, roof_ridge_alignment, xy_accuracy_buildings,z_accuracy,density_check,xy_precision_buildings
import glob
LOGDIR=os.path.join(os.path.dirname(__file__),"logs")
MAX_PROCESSES=4
def usage():
	print("Usage:\n%s <test> <las_files> [<vector_tile_root>] -use_local" %os.path.basename(sys.argv[0]))
	print(" ")
	print("<test>:  ")
	print("         Which test to run, currently:")
	print("         'road'                  - precision on roads")
	print("         'build' or 'byg'        - precision on buildings")
	print("         'class'                 - classification check")
	print("         'count'                 - classes in las tile")
	print("         'roof_ridges' or 'roof' - check roof ridges")
	print("         'corners'               - check building corners.")
	print("         'xy_precision'          - check xy precision based on building corners.")
	print("         'z_abs'                 - absoulte z check for 3D-line segments (e.g. roads) or 3D-point patches ")
	print("         'density'               - run density check wrapper (wrapping 'page')")
	print(" ")
	print("<las_files>: ")
	print("         list of las files to run, e.g. c:\\test\\*.las ")
	print(" ")
	print("<vector_tile_root>: ")
	print("         ONLY relevant for those checks which use vector data reference input.")
	print("         Root of a 'standard' directory of vector tiles ")
	print("         clipped into 1km blocks and grouped in 10 km ")
	print("         subdirs (see definition in utils.names). This")
	print("         directory must contain vector tile of the ")
	print("         appropriate geometry type for the chosen check.")
	print(" ")
	print("-use_local (optional): ")
	print("         Forces use of local db for reporting.")
	print("-mp <n_processes> (optional):")
	print("         Control the maximal number of processes to spawn. Defaults to 4.")
	print("-runid <id>  Specify id for this run. Will otherwise be NULL.")
	print(" ")
	print("Additional arguments will be passed on to the selected test script...")
	sys.exit(1)

def run_check(p_number,testname,file_pairs,add_args,runid):
	if testname=="z_roads":
		test_func=z_precision_roads.main
	elif testname=="z_build":
		test_func=z_precision_buildings.main
	elif testname=="classification":
		test_func=classification_check.main
	elif testname=="count":
		test_func=count_classes.main
	elif testname=="roof_ridges":
		test_func=roof_ridge_alignment.main
	elif testname=="corners":
		test_func=xy_accuracy_buildings.main
	elif testname=="xy_precision":
		test_func=xy_precision_buildings.main
	elif testname=='z_abs':
		test_func=z_accuracy.main
	elif testname=='density':
		test_func=density_check.main
	else:
		print("Invalid test name")
		return
	if runid is not None:
		report.set_run_id(runid)
	logname=testname+"_"+(time.asctime().split()[-2]).replace(":","_")+"_"+str(p_number)+".log"
	logname=os.path.join(LOGDIR,logname)
	logfile=open(logname,"w")
	stdout=redirect_output.redirect_stdout(logfile)
	stderr=redirect_output.redirect_stderr(logfile)
	sl="*-*"*23
	print(sl)
	print("Running %s rutine at %s, process: %d, run id: %s" %(testname,time.asctime(),p_number,runid))
	print(sl)
	print("%d input file pairs" %len(file_pairs))
	done=0
	for lasname,vname in file_pairs:
		print(sl)
		print("Doing lasfile %s..." %lasname)
		send_args=[testname,lasname]
		if len(vname)>0:
			send_args.append(vname)
		send_args+=add_args
		test_func(send_args)
		done+=1
	print("Checked %d tiles, finished at %s" %(done,time.asctime()))
	#avoid writing to a closed fp...
	stdout.close()
	stderr.close()
	logfile.close()
		
def main(args):
	if len(args)<3:
		usage()
	if "-use_local" in args:
		#will do nothing if it already exists
		#should be done 'process safe' so that its available for writing for the child processes...
		report.create_local_datasource() 
	if "-mp" in args:
		i=args.index("-mp")
		max_processes=int(args[i+1])
		del args[i:i+2]
	else:
		max_processes=MAX_PROCESSES
	if "-runid" in args:
		i=args.index("-runid")
		runid=int(args[i+1])
	else:
		runid=None
	# NOW for the magic conditional import of qc module
	testname=args[1]
	#hmmm this logic might get a bit too 'simplistic' e.g. abs_road will give z_roads... TODO: fix that
	use_vector_data=True  #signals that we should match a las tile to a vector data tile of some sort...
	if "road" in testname:
		testname="z_roads"
	elif "build" in testname or "byg" in testname:
		testname="z_build"
	elif "class" in testname:
		testname="classification"
	elif "roof" in testname:
		testname="roof_ridges"
	elif "corners" in testname:
		testname="corners"
	elif "xy_precision" in testname:
		testname="xy_precision"
	elif "abs" in testname:
		testname="z_abs"
	elif "density" in testname:
		testname="density"
	elif "count" in testname:
		testname="count"
		use_vector_data=False
	else:
		print("%s not matched to any test (yet....)" %testname)
		usage()
	las_files=glob.glob(args[2])
	if len(las_files)==0:
		print("Sorry, no input las files found.")
		usage()
	
	print("Running qc_wrap at %s" %(time.asctime()))
	if not os.path.exists(LOGDIR):
		os.mkdir(LOGDIR)
	t1=time.clock()
	if use_vector_data:
		if len(args)<4:
			usage()
		add_args=args[4:] #possibly empty slice...
		vector_root=args[3]
		if not os.path.exists(vector_root):
			print("Sorry, %s does not exist" %vector_root)
			usage()
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
	else:  #else just append an empty string to the las_name...
		matched_files=[(name,"") for name in las_files] 
		add_args=args[3:]
		print("Found %d las files." %len(matched_files))
	if len(matched_files)>0:
		n_tasks=max(min(int(len(matched_files)/2),max_processes),1)
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
			p = Process(target=run_check, args=(i,testname,files_to_do,add_args,runid,))
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