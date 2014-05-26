##############
## Stats module
#############
import numpy as np
import sys
DEBUG=False
if DEBUG:
	import matplotlib
	matplotlib.use("Qt4Agg")
	import matplotlib.pyplot as plt
	
def get_dz_stats(dz,remove_outliers=True):
	m=dz.mean()
	sd=np.std(dz)
	l1=np.fabs(dz).mean()
	rms=np.sqrt((dz**2).mean())
	print("Raw statistics:")
	print("Number of points: %d" %dz.shape[0])
	print("Mean dz:          %.4f m" %m)
	print("Std. dev of dz:   %.4f" %sd)
	print("Mean abs. error:  %.4f m" %l1)
	print("RMS            :  %.4f m" %rms)
	if remove_outliers:
		print("Removing outliers...")
		M=np.fabs(dz-m)<(2.5*sd)
		i=0
		while not M.all() and i<5:
			i+=1
			dz=dz[M]
			m=dz.mean()
			sd=np.std(dz)
			l1=np.fabs(dz).mean()
			M=np.fabs(dz-m)<(2*sd)
			rms=np.sqrt((dz**2).mean())
		if (i>0):
			print("Statistics after %d iteration(s)" %i)	
			print("Number of points: %d" %dz.shape[0])
			print("Mean dz:          %.4f m" %m)
			print("Std. dev of dz:   %.4f" %sd)
			print("Mean abs. error:  %.4f m" %l1)
			print("RMS            :  %.4f m" %rms)
		else:
			print("No outliers...")
	if DEBUG:
		plt.figure()
		plt.hist(dz)
		plt.show()
	return m,sd,l1,rms,dz.shape[0]