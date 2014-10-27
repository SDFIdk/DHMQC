########################################
## Wrapper to run sequences of commands in parallell
## #####################################
import os,sys,time, shlex
import multiprocessing , subprocess
import argparse

#for now, we dont care about stdout, etc...
def run_command(pid,cmd):
	cmd=shlex.split(cmd)
	rc=subprocess.call(cmd)
	sys.exit(rc)   #set the exitcode
	

def main(args):
	parser=argparse.ArgumentParser(description="Wrapper rutine for running a number of commands (e.g. batch files) in parallel")
	parser.add_argument("commands",nargs="+",help="commands to run, e.g. shell scripts.")
	pargs=parser.parse_args(args[1:])
	tasks=[]
	names=[]
	for i,cmd in enumerate(pargs.commands):
		p = multiprocessing.Process(target=run_command, args=(i,cmd))
		tasks.append(p)
		p.start()
		if len(cmd)>64:
			name=cmd[:64]+"..."
		else:
			name=cmd
		names.append(name)
	time.sleep(5)
	n_alive=len(multiprocessing.active_children())
	while n_alive>0:
		time.sleep(5)
		for i in range(len(tasks)):
			p=tasks[i]
			alive=p.is_alive()
			name=names[i]
			if alive:
				print("[rip]: {0:s}: is still running".format(name))
			n_alive+=int(alive)
		print("[rip]: active {0:d}".format(n_alive))
		
	n_errs=0
	for i in range(len(tasks)):
		p=tasks[i]
		name=names[i]
		print("[rip]: {0:s} finished with code {1:d}".format(name,p.exitcode))
		n_errs+=(p.exitcode!=0)
	print("[rip]: Seemingly {0:d} error(s)...".format(n_errs))
	



if __name__=="__main__":
	main(sys.argv)

	
	
			
	
		
		

