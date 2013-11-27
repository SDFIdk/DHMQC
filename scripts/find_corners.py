####################
## Find planes - works for 'simple houses' etc...
## Useful for finding house edges (where points fall of a plane) and roof 'ridges', where planes intersect...
## work in progress...
###########################

import sys,os
from thatsDEM import pointcloud, vector_io, array_geometry
import numpy as np
import matplotlib
from math import degrees,radians,acos,tan
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
				here=[a,b,c_m,h[i],alpha]   
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

def cluster(pc):
	#Check horisontal planes first#
	#z_p=find_horisontal_planes(pc.z)
	#if z_p is not None:
	#	print(" A horisontal plane at z= %.3f" %z_p)
	#xy_t=pc.xy.mean(axis=0)
	#z_t=pc.z.mean()
	#xy=pc.xy-xy_t
	#z=pc.z-z_t
	#plot3d(xy,z)
	xy=pc.xy
	z=pc.z
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
		if DEBUG:
			for f in final_candidates:
				print f
				z1=f[0]*xy[:,0]+f[1]*xy[:,1]+f[2]
				plot3d(xy,z,z1)
	#transform back...
	#for p in final_candidates:
	#	p[2]+=z_t-(p[0]*xy_t[0]+p[1]*xy_t[1])
	return final_candidates
		
def find_planar_pairs(planes):
	best_score=1000
	pair=None
	eq=None
	for i in range(len(planes)):
		p1=planes[i]
		for j in range(i,len(planes)):
			p2=planes[j]
			score=40/(p1[-1]+p2[-1])*((p1[0]+p2[0])**2+(p1[1]+p2[1])**2)
			if score<best_score:
				pair=(i,j)
				best_score=score
	if pair is not None:
		p1=planes[pair[0]]
		p2=planes[pair[1]]
		eq=(p1[0]-p2[0],p1[1]-p2[1],p2[2]-p1[2])  #ax+by=c
	return pair,eq
				

def plot3d(xy,z1,z2=None,z3=None):
	fig = plt.figure()
	ax = Axes3D(fig)
	ax.scatter(xy[:,0], xy[:,1], z1,s=1.7)
	if z2 is not None:
		ax.scatter(xy[:,0], xy[:,1], z2,s=3.0,color="red")
	if z3 is not None:
		ax.scatter(xy[:,0], xy[:,1], z3,s=3.0,color="green")
	plt.show()


def plot_points(a_poly,points):
	plt.figure()
	plt.axis("equal")
	plt.plot(a_poly[:,0],a_poly[:,1],label="Polygon")
	plt.scatter(points[:,0],points[:,1],label="edges",color="red")
	plt.legend()
	plt.show()

def get_intersections(poly,line):
	#hmmm - not many vertices, probably fast enough to run a python loop
	#TODO: test that all vertices are corners...
	intersections=[]
	a_line=np.array(line[:2])
	n_line=np.sqrt((a_line**2).sum())
	for i in xrange(poly.shape[0]-1): #polygon is closed...
		v=poly[i+1]-poly[i] #that gives us a,b for that line
		n_v=np.sqrt((v**2).sum())
		cosv=np.dot(v,a_line)/(n_v*n_line)
		a=degrees(acos(cosv))
		#print("Angle between normal and input line is: %.4f" %a)
		if abs(a)>20 and abs(a-180)>20:
			continue
		else:
			n2=np.array((-v[1],v[0])) #normal to 'vertex' line
			c=np.dot(poly[i],n2)
			A=np.vstack((n2,a_line))
			xy=np.linalg.solve(A,(c,line[2]))
			xy_v=xy-poly[i]
			# check that we actually get something on the line...
			n_xy_v=np.sqrt((xy_v**2).sum())
			cosv=np.dot(v,xy_v)/(n_v*n_xy_v)
			if abs(cosv-1)<0.01 and n_xy_v/n_v<1.0:
				center=poly[i]+v*0.5
				d=np.sqrt(((center-xy)**2).sum())
				cosv=np.dot(n2,a_line)/(n_v*n_line)
				rot=degrees(acos(cosv))-90.0
				print("Distance from intersection to line center: %.4f m" %d)
				print("Rotation:                                  %.4f dg" %rot)
				intersections.append(xy.tolist())
	return np.asarray(intersections)
		
cut_angle=1.0
z_limit=2.0
#Now works for 'simple' houses...	
def main(args):
	lasname=args[1]
	polyname=args[2]
	pc=pointcloud.fromLAS(lasname).cut_to_class(1).cut_to_z_interval(-10,200)
	polys=vector_io.get_geometries(polyname)
	fn=0
	for poly in polys:
		fn+=1
		a_poly=array_geometry.ogrgeom2array(poly)
		pcp=pc.cut_to_polygon(a_poly)
		if pcp.get_size()<500:
			print("Few points in polygon...")
			continue
		#Go to a more numerically stable coord system - from now on only consider outer ring...
		a_poly=a_poly[0]
		pcp.triangulate()
		geom=pcp.get_triangle_geometry()
		m=geom[:,1].mean()
		sd=geom[:,1].std()
		if (m>1.5 or 0.5*sd>m):
			print("Feature %d, bad geometry...." %fn)
			print m,sd
			continue
		#geom is ok - we proceed with a buffer around da house
		poly_buf=poly.Buffer(2.0)
		a_poly2=array_geometry.ogrgeom2array(poly_buf)
		pcp=pc.cut_to_polygon(a_poly2)
		pcp.triangulate()
		geom=pcp.get_triangle_geometry()
		tanv2=tan(radians(cut_angle))**2
		mask=np.where(np.logical_and(geom[:,0]>tanv2,geom[:,2]>z_limit))[0]
		mask=mask.astype(np.int32)
		triangles=pcp.triangulation.get_triangles(mask)
		p1=pcp.xy[triangles[:,0]]
		p2=pcp.xy[triangles[:,1]]
		p3=pcp.xy[triangles[:,2]]
		z1=pcp.z[triangles[:,0]]
		z2=pcp.z[triangles[:,1]]
		z3=pcp.z[triangles[:,2]]
		z=np.column_stack((z1,z2,z3))
		points=np.column_stack((p1,p2,p3))
		m=np.argmax(z,axis=1)*2
		out=np.empty_like(p1)
		for i in range(out.shape[0]):
			out[i]=points[i,m[i]:m[i]+2]
		plot_points(a_poly,out)
			
		
		
	


if __name__=="__main__":
	main(sys.argv)