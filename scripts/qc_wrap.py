import sys,os,time
from utils import redirect_output,names
import glob
def usage():
	print("Call:\n%s <test> <las_files> <vector_tile_root> -use_local" %os.path.basename(sys.argv[0]))
	print("The <test> argument will decide which test to run, currently:")
	print("zcheck_road or anytning containing 'road': import zcheck_road")
	print("zhceck_build or anything containing 'build': import zcheck_build / zcheck_byg")
	print("classification_check or anything containing 'class': import classification check")
	print("<vector_tile_root> is the root of a 'standard' directory of vector tiles clipped into 1km blocks,")
	print("and grouped in 10 km subdirs (see definition in utils.names)")
	print("This directory must contain vector tile of the appropriate geometry type for the chosen check.")
	print("-use_local optional. Forces use of local db for reporting.")
	print("The <las_file> argument could be e.g. C:/abc/las/*.las")
	print("Additional arguments will be passed on to the selected test script...")
	sys.exit(1)

args=sys.argv
if len(args)<4:
	usage()
# NOW for the magic conditional import of qc module
testname=args[1]
if "road" in testname:
	import zcheck_road as test
elif "build" in testname or "byg" in testname:
	import zcheck_byg as test
elif "class" in testname:
	import classification_check as test
else:
	print("%s not mathed to any test (yet....)")
	usage()
las_files=glob.glob(args[2])
vector_root=args[3]
if not os.path.exists(vector_root):
	print("Sorry, %s does not exist" %vector_root)
	usage()
progname=os.path.splitext(os.path.basename(args[0]))[0]
logname=progname+"_"+time.asctime().replace(" ","_").replace(":","_")+".log"
logfile=open(logname,"w")
stdout=redirect_output.redirect_stdout(logfile)
stderr=redirect_output.redirect_stderr(logfile)
sl="*-*"*23
print(sl)
print("Running %s at %s" %(progname,time.asctime()))
print("Running tests from %s" %os.path.basename(test.__file__))
print(sl)
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
	if len(args)>4:
		send_args+=args[4:]
	test.main(send_args)
	done+=1
print("Checked %d tiles, finished at %s" %(done,time.asctime()))
#avoid writing to a closed fp...
stdout.close()
stderr.close()
logfile.close()
sys.exit(0)
	