import sys,os,time,importlib
from multiprocessing import Process, Queue
from qc.thatsDEM import report
from qc.utils import redirect_output,names
import qc
import glob
LOGDIR=os.path.join(os.path.dirname(__file__),"logs")
MAX_PROCESSES=4
def usage():
	print("Usage:\n%s <test> <las_files|list_file> [<vector_tile_root>] -use_local" %os.path.basename(sys.argv[0]))
	print(" ")
	print("<test>:  ")
	print("         Which test to run, currently:")
	for t in qc.tests:
		print("               "+t)
	print(" ")
	print("<las_files|list_file>: ")
	print("         glob pattern of las files to run, e.g. c:\\test\\*.las ")
	print("         or a list file containing paths to las files, one per line.")
	print("         If the pattern only matches one file, which does not end with 'las' a list file is assumed.")
	print(" ")
	print("<vector_tile_root>: ")
	print("         ONLY relevant for those checks which use vector data reference input.")
	print("         Root of a 'standard' directory of vector tiles ")
	print("         clipped into 1km blocks and grouped in 10 km ")
	print("         subdirs (see definition in utils.names). This")
	print("         directory must contain vector tile of the ")
	print("         appropriate geometry type for the chosen check.")
	print(" ")
	print("-usage to print usage of selected test.")
	print("-ext <ref_data_extension> (optional):")
	print("         Specify extension of ref-data (default) .shp")
	print("-single_dir (optional):")
	print("         Override the default layout for reference tiles.")
	print("         Specifies that reference tiles are located in a single dir!")
	print("-use_local (optional): ")
	print("         Forces use of local db for reporting.")
	print("-mp <n_processes> (optional):")
	print("         Control the maximal number of processes to spawn. Defaults to 4.")
	print("-runid <id>  Specify id for this run. Will otherwise be NULL.")
	print("-schema <schema name>  Specify schema name for this block. Default dhmqc.")
	print("         NOT supported for local datasource.")
	print(" ")
	print("Additional arguments will be passed on to the selected test script...")
	sys.exit(1)

def run_check(p_number,testname,file_pairs,add_args,runid,schema):
	test_func=qc.get_test(testname)
	if runid is not None:
		report.set_run_id(runid)
	report.set_schema(schema)
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
	if "-ext" in args:
		i=args.index("-ext")
		ext=args[i+1]
		del args[i:i+2]
		if not ext.startswith("."):
			ext="."+ext
	else:
		ext=".shp"
	if "-single_dir" in args:
		i=args.index("-single_dir")
		del args[i]
		simple_layout=True
		print("Assuming layout in a single dir...")
	else:
		simple_layout=False
	if "-runid" in args:
		i=args.index("-runid")
		runid=int(args[i+1])
	else:
		runid=None
	
	if "-schema" in args:
		i=args.index("-schema")
		schema=(args[i+1])
		if "-use_local" in args:
			print("Error: use_local does not support schema names.")
			return
		#Test if we can open the global datasource with given schema
		ds=report.get_output_datasource()
		if ds is None:
			print("Unable to open global datasource...")
			return 
		layers=report.LAYERS.keys()
		#only test if we can open one of the layers...
		layer_name=layers[0].replace("dhmqc",schema)
		layer=ds.GetLayerByName(layer_name)
		if layer is None:
			print("Unable to fetch layer "+layer_name+"\nSchema "+schema+" probably not created!")
			return
		layer=None
		ds=None
	else:
		schema="dhmqc"	
	# NOW for the magic conditional import of qc module
	testname=args[1].replace(".py","")
	
	if not testname in qc.tests:
		print("%s not matched to any test (yet....)" %testname)
		usage()
	sys.argv[0]=testname
	if "-usage" in args:
		test_usage=qc.usage(testname)
		if test_usage is not None:
			print("Usage for "+testname)
			test_usage()
		else:
			print("No usage for "+testname)
		sys.exit()
	use_vector_data=qc.tests[testname]
	las_files=glob.glob(args[2])
	if len(las_files)==0:
		print("Sorry, no input (las or list) file(s) found.")
		usage()
	if len(las_files)==1 and (not las_files[0].endswith("las")):
		print("Getting las files from input list...")
		list_file=las_files[0]
		las_files=[]
		f=open(list_file)
		for line in f:
			sline=line.strip()
			if len(sline)>0 and sline[0]!="#":
				if not os.path.exists(sline):
					print("%s does not exist!" %sline)
				else:
					las_files.append(sline)
		print("Found %d existing las filenames." %len(las_files))
		f.close()
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
				vector_tile=names.get_vector_tile(vector_root,fname,ext,simple_layout)
			except ValueError,e:
				print(str(e))
				continue
			if vector_tile is None:
				print("Reference tile corresponding to %s does not exist!" %os.path.basename(fname))
				continue
			matched_files.append((fname,vector_tile))
		print("%d las files matched with reference tiles." %len(matched_files))
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
			p = Process(target=run_check, args=(i,testname,files_to_do,add_args,runid,schema,))
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