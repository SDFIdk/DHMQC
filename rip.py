########################################
## Wrapper to run commands in parallell
## For logically distinct tasks - each which migth consist of a connected sequence of tasks.
## The command line interface is primitive - just a list of commands... could add support for a json-file spec.
## Import as module for a richer interface...
## #####################################
import os,sys,time, shlex
import multiprocessing , subprocess, logging
import argparse

#should probably log error to a file... TODO....
def run_commands(pid,cmds):
	#run a connected group of commands
	for cmd in cmds:
		cmd=shlex.split(cmd)
		prc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=-1)
		stdout,stderr=prc.communicate()
		rc=prc.poll()
		if stderr is not None and len(stderr)>0:
			logger = multiprocessing.log_to_stderr()
			logger.error(stderr)
		if rc!=0: #break on error
			sys.exit(rc) 
	sys.exit(0)

#a sequence of sequences... e.g. [["doit.exe a b","dosommore.exe b c"],["dosomethingelse.exe x y","andthenthat.exe y z"]]
def rip(cmd_groups):
	tasks=[]
	names=[]
	for i,cmds in enumerate(cmd_groups):
		if isinstance(cmds,str) or isinstance(cmds,unicode):
			cmds=[cmds]
		cmds=list(cmds)
		p = multiprocessing.Process(target=run_commands, args=(i,cmds))
		tasks.append(p)
		p.start()
		cmd=cmds[0]
		if len(cmd)>64:
			name=cmd[:64]+"..."
		else:
			name=cmd
		if len(cmds)>1:
			name+="+{0:d} cmds".format(len(cmds)-1)
		name='"'+name+'"'
		names.append(name)
		print("[rip]: starting "+name)
	print("[rip]: {0:d} tasks started...".format(len(tasks)))
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

def main(args):
	#The command line interface is primitive - just a list of commands... could add support for a json-file spec.
	# import as module for a richer interface...
	parser=argparse.ArgumentParser(description="Wrapper rutine for running a number of commands (e.g. batch files) in parallel")
	parser.add_argument("commands",nargs="+",help="commands to run, e.g. shell scripts.")
	pargs=parser.parse_args(args[1:])
	rip(pargs.commands)
	
	



if __name__=="__main__":
	main(sys.argv)

	
	
			
	
		
		

