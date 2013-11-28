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
DEBUG="-debug" in sys.argv


#ax+by=c - and we restrict a,b to lie on S^1
def search(xy,v1=0,v2=180,look_lim=0.1,bin_size=0.3,steps=30,look_for=None):
	V=np.radians(np.linspace(v1,v2,steps)) #angles in RP^1 (ie spanning not more than 180 dg)
	A=np.cos(V)
	B=np.sin(V)
	h_max=-1
	found=[]
	found_max=None
	#N=np.sqrt((xy**2).sum(axis=1))
	#house_rad=N.max()
	#for now will only one candidate for each pair of a,b
	for i in xrange(A.shape[0]):
		v=degrees(V[i])
		c=A[i]*xy[:,0]+B[i]*xy[:,1] #we project the points onto an axis, large bins away from zero should correspond to a line...
		c2=c.max()
		c1=c.min()
		house_rad=c2-c1
		n=int(np.round((c2-c1)/bin_size))
		h,bins=np.histogram(c,n)
		h=h.astype(np.float64)/c.size
		bin_centers=(bins[0:-1]+bins[1:])*0.5
		if look_for is None:
			M=np.logical_or(np.fabs(bin_centers-c1)<5*bin_size,np.fabs(bin_centers-c2)<5*bin_size)
		else:
			M=(np.fabs(bin_centers-look_for)<5*bin_size)
		I=np.where(np.logical_and(h>look_lim,M))[0]
		#if I.size>0 and False:
		#	plt.hist(c)
		#	plt.xlabel("Angle: %.2f" %v)
		#	plt.show()
		for j in I:
			c_m=bin_centers[j]
			here=[A[i],B[i],c_m,h[j],v] 
			#print c_m, house_rad, h[j],v,look_lim
			if h[j]>h_max:
				found_max=here
				h_max=h[j]
			found.append(here)
	return found_max,found



def cluster_2d(xy):
	fmax,found=search(xy,0.0,180.0,0.02,0.4)
	print fmax, len(found), "found1"
	final_candidates=[]
	if len(found)>0:
		for line in found:
			v=line[-1]
			c=line[2]
			#print "closer look for v: ",v,line[3]
			fmax,found2=search(xy,v-2,v+2,0.06,0.3,steps=30,look_for=c)
			if fmax is None:
				continue
			#print "result:", fmax[-1],fmax[3]
			fmax=np.asarray(fmax)
			if fmax[3]>0.06: 
				if len(final_candidates)==0:
					final_candidates=[fmax]
					continue
				do_keep=True
				keep=[]
				for i in range(len(final_candidates)):
					stored=final_candidates[i]
					v_diff=fmax[4]-stored[4]
					if (abs(v_diff-180)<15):
						s=-1
					else:
						s=1
					if (abs(v_diff)<15 or abs(v_diff-180)<15) and abs(s*fmax[2]-stored[2])<1.8: #check if a similar line is already stored
						if fmax[3]<stored[3]:
							do_keep=False
							keep=final_candidates
							break
						
					else:
						keep.append(stored)
				
				if do_keep:
					keep.append(fmax)
				final_candidates=keep
				
		if DEBUG:
			for f in final_candidates:
				if abs(f[0])>abs(f[1]):
					x=(f[2]-xy[:,1]*f[1])/f[0]
					xy2=np.column_stack((x,xy[:,1]))
				else:
					y=(f[2]-xy[:,0]*f[0])/f[1]
					xy2=np.column_stack((xy[:,0],y))
				print f,"dist"
				plot_points2(xy,xy2)
	return final_candidates
	
		
def plot_points2(xy1,xy2):
	plt.figure()
	plt.axis("equal")
	plt.scatter(xy1[:,0],xy1[:,1],label="noisy",color="red")
	plt.scatter(xy2[:,0],xy2[:,1],label="adjusted",color="green")
	plt.legend()
	plt.show()


def plot_points(a_poly,points):
	plt.close("all")
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
		
cut_angle=45.0
z_limit=2.0
#Now works for 'simple' houses...	
def main(args):
	lasname=args[1]
	polyname=args[2]
	pc=pointcloud.fromLAS(lasname).cut_to_z_interval(-10,200).cut_to_class([1,2])
	polys=vector_io.get_geometries(polyname)
	fn=0
	for poly in polys:
		fn+=1
		a_poly=array_geometry.ogrgeom2array(poly)
		pcp=pc.cut_to_polygon(a_poly)
		if pcp.get_size()<500:
			print("Few points in polygon...")
			continue
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
		print("Points in buffer: %d" %pcp.get_size())
		pcp.triangulate()
		geom=pcp.get_triangle_geometry()
		tanv2=tan(radians(cut_angle))**2
		#set a mask to mark the triangles we want to consider as marking the house boundary
		mask=np.logical_and(geom[:,0]>tanv2,geom[:,2]>z_limit)
		#we consider the 'high' lying vertices - could also just select the highest of the three vertices... 
		p_mask=(pcp.z>pcp.z.min()+2)
		#and only consider those points which lie close to the outer bd of the house...
		p_mask&=array_geometry.points_in_buffer(pcp.xy,a_poly,1.2) #a larger shift than 1.2 ??
		#this just selects vertices where p_mask is true, from triangles where mask is true - nothing else...
		bd_mask=pcp.get_boundary_vertices(mask,p_mask)
		bd_pts=pcp.xy[bd_mask]
		plot_points(a_poly,pcp.xy[bd_mask])
		xy_t=bd_pts.mean(axis=0)
		xy=bd_pts-xy_t
		print xy.mean(axis=0)
		cluster_2d(xy)
			
		
		
	


if __name__=="__main__":
	main(sys.argv)