####################
## Find planes - works for 'simple houses' etc...
## Useful for finding house edges (where points fall of a plane) and roof 'ridges', where planes intersect...
## work in progress...
###########################

import sys,os
from thatsDEM import pointcloud, vector_io, array_geometry
import numpy as np
import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
DEBUG=False


def find_horisontal_planes(z, bin_size=0.1):
	#improve this alot...
	sd=np.std(z)
	z1=z.min()
	z2=z.max()
	n=max(int(np.round(z2-z1)/bin_size),1)
	h,bins=np.histogram(z,n)
	h=h.astype(np.float64)/z.size
	#TODO: real clustering
	i=np.argmax(h)
	i0=i
	i1=i
	t=h[i]
	if (i>0):
		t+=h[i-1]
		i0=i-1
	if (i<z.size-1):
		t+=h[i+1]
		i1=i+1
	if (t>0.5):
		M=np.logical_and(z>=bins[i0],z<=bins[i1+1])
		return np.mean(z[M])
	return None
	
def search(a1,a2,b1,b2,xy,z,look_lim=0.1,bin_size=0.2):
	A=np.linspace(a1,a2,15)
	B=np.linspace(b1,b2,15)
	h_max=-1
	found=[]
	found_max=None
	#for now will only one candidate for each pair of a,b
	for a in A:
		for b in B:
			found_here=[]
			alpha=np.arctan(np.sqrt(a**2+b**2))*180/np.pi
			if alpha<10:
				continue
			c=z-a*xy[:,0]-b*xy[:,1]
			c2=c.max()
			c1=c.min()
			n=int(np.round((c2-c1)/bin_size))
			h,bins=np.histogram(c,n)
			h=h.astype(np.float64)/c.size
			i=np.argmax(h)
			if h[i]>look_lim and h[i]>3*h.mean():
				c_m=(bins[i]+bins[i+1])*0.5
				here=(a,b,c_m,h[i],alpha)
				if h[i]>h_max:
					found_max=here
					h_max=h[i]
				found.append(here)
			#I=np.where(np.logical_and(h>look_lim,h>3*h.mean()))[0]
			#print h.mean(),h.std(),h.max()
			#print "limit would be:", h.mean()+3*h.std()
			#if I.size>0:
			#	plt.close("all")
			#	plt.figure()
			#	plt.hist(c,n)
			#	plt.title("fn: %d, a: %.3f, b: %3.f, alpha: %.3f, d_max: %.2f, n: %d" %(fn,a,b,alpha,h.max(),n))
			#	plt.show()
			#for i in I:
			#	c_m=(bins[i]+bins[i+1])*0.5
			#	here=(a,b,c_m,h[i],alpha)
			#	if h[i]>h_max:
			#		found_max=here
			#		h_max=h[i]
					#plt.hist(h)
					#plt.show()
			#	found.append(here)
	return found_max,found

def cluster(pc,fn):
	pc.triangulate()
	geom=pc.get_triangle_geometry()
	if (geom[:,1].mean()>1.5 or geom[:,1].std()>1):
		print("Feature number %d bad geometry, continuing..." %fn)
		return
	#Check horisontal planes first#
	z_p=find_horisontal_planes(pc.z)
	if z_p is not None:
		print(" A horisontal plane at z= %.3f" %z_p)
	xy_t=pc.xy.mean(axis=0)
	z_t=pc.xy.mean()
	xy=pc.xy-xy_t
	z=pc.z-z_t
	plot3d(xy,z)
	fmax,found=search(-2.5,2.5,-2.5,2.5,xy,z,0.05)
	#print fn,"*"*70,len(found)
	final_candidates=[]
	if len(found)>0:
		#print "feature no %d, found: %d" %(fn,len(found))
		for plane in found:
			#print f
			a,b=plane[0],plane[1]
			#print "closer look"
			fmax,found2=search(a-0.3,a+0.3,b-0.3,b+0.3,xy,z,0.05,0.1)
			if fmax is None:
				continue
			#print fmax
			if fmax[3]>0.1: #at least 10 pct...
				replaced_other=False
				for i in range(len(final_candidates)):
					stored=final_candidates[i]
					if max(abs(fmax[0]-stored[0]),abs(fmax[1]-stored[1]))<0.1 and fmax[3]>stored[3]: #check if a similar plane already stored
						final_candidates[i]=fmax #if so store the most popular of the two...
						replaced_other=True
						break
				if not replaced_other:
					final_candidates.append(fmax)
		for f in final_candidates:
			print f
			z1=f[0]*xy[:,0]+f[1]*xy[:,1]+f[2]
			pip=pointcloud.Pointcloud(xy,z,z1)
			plot3d(xy,z,z1)
			

def plot3d(xy,z1,z2=None):
	fig = plt.figure()
	ax = Axes3D(fig)
	ax.scatter(xy[:,0], xy[:,1], z1,s=1.7)
	if z2 is not None:
		ax.scatter(xy[:,0], xy[:,1], z2,s=3.0,color="red")
	plt.show()
	
	
def main(args):
	lasname=args[1]
	polyname=args[2]
	#lasname="../../dhm/las/1km_6169_451.las"
	#polyname="../../dhm/byg/10km_616_45/1km_6169_451.shp"
	pc=pointcloud.fromLAS(lasname).cut_to_class(1)
	polys=vector_io.get_geometries(polyname)
	fn=0
	for poly in polys:
		fn+=1
		a_poly=array_geometry.ogrgeom2array(poly)
		pcp=pc.cut_to_polygon(a_poly)
		#plot3d(pcp)
		cluster(pcp,fn)
		


if __name__=="__main__":
	main(sys.argv)