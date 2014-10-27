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
	for i,cmd in enumerate(pargs.commands):
		p = multiprocessing.Process(target=run_command, args=(i,cmd))
		tasks.append(p)
		p.start()
	n_alive=len(tasks)
	while n_alive>0:
		time.sleep(3)
		n_alive=0
		for i in range(len(tasks)):
			p=tasks[i]
			alive=p.is_alive()
			cmd=pargs.commands[i]
			if len(cmd)>64:
				name=cmd[:64]+"..."
			else:
				name=cmd
			if alive:
				print("[rip]: {0:s}: is still running".format(name))
			else:
				print("[rip]: {0:s}: finished with code {1:d}".format(name,p.exitcode))
			n_alive+=int(alive)
		print("[rip]: active {0:d}".format(n_alive))



if __name__=="__main__":
	main(sys.argv)

	
	
			
	
		
		

