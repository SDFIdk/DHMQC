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

def norm(x):
	return np.sqrt((x**2).sum(axis=1))

def residuals(p1,p2,xy):
	N=(p2-p1)
	n=np.sqrt(N.dot(N))
	N=N/n
	xy_t=xy-p1
	p=np.dot(xy_t,N)
	P=np.empty_like(xy)
	P[:]=N
	P*=p.reshape((xy.shape[0],1))
	return xy_t-P,p
	
def find_line(p1,p2,pts): #linear regression, brute force or whatever...
	N=(p2-p1)
	n=np.sqrt(N.dot(N))
	N/=n
	N=np.asarray((-N[1],N[0]))
	if (N[1]<0):
		N*=-1 #we want N to be in the upper half plane
	c=np.dot(p1,N)
	angle=np.degrees(np.arccos(N[0]))
	print("Pre: %.3f, %.4f, %.4f, %.4f" %(angle,N[0],N[1],c))
	found=search(pts,angle-2.5,angle+2.5,30)
	print("Post: %.3f, %.4f, %.4f, %.4f" %(found[-1],found[0],found[1],found[2]))
	
	if DEBUG:
		f=found
		xy=np.row_stack((p1,p2))
		if abs(f[0])>abs(f[1]):
			x=(f[2]-xy[:,1]*f[1])/f[0]
			xy2=np.column_stack((x,xy[:,1]))
		else:
			y=(f[2]-xy[:,0]*f[0])/f[1]
			xy2=np.column_stack((xy[:,0],y))
		plot_points2(pts,xy2,xy)
	return found

#brute force - todo: real linear regression...
def search(xy,v1=0,v2=180,steps=30):
	V=np.radians(np.linspace(v1,v2,steps)) #angles in RP^1 (ie spanning not more than 180 dg)
	A=np.cos(V)
	B=np.sin(V)
	best=1e6
	found=None
	for i in xrange(A.shape[0]):
		v=degrees(V[i])
		c=A[i]*xy[:,0]+B[i]*xy[:,1]  #really a residual...
		badness=np.var(c)   
		if badness<best:
			found=[A[i],B[i],c.mean(),v] #the mean, minimizes the square distance sum (Karsten Grove)
			best=badness
	return found

def plot_points2(xy1,xy2,xy3=None):
	plt.figure()
	plt.axis("equal")
	plt.scatter(xy1[:,0],xy1[:,1],label="noisy",color="red")
	plt.plot(xy2[:,0],xy2[:,1],label="adjusted",color="green")
	if xy3 is not None:
		plt.plot(xy3[:,0],xy3[:,1],label="polygon input",color="blue")
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


def check_distribution(p1,p2,xy):
	d=p2-p1
	l=np.sqrt(d.dot(d))
	r,p=residuals(p1,p2,xy) #we can dot this with normal vector, orjust take the norm.
	n=norm(r)
	#test that we have a good fraction of points close to the line and that they are evenly distributed
	M=np.logical_and(p>=0,p<=l)
	M&=(n<1)
	p=p[M]
	r=r[M]
	if r.size<10:
		return False,None
	n_bins=10
	if DEBUG and False:
		plt.hist(p,n_bins)
		plt.xlabel("pmax: %.4f, l: %.4f" %(p.max(),l))
		plt.show()
	f=(M.sum()/float(M.size))
	print("Fraction of points 'close' to line %.3f" %f)
	h,bins=np.histogram(p,n_bins)
	h=h.astype(np.float64)/p.size
	if (h<0.05).sum()>3:
		print("Uneven distribution!")
		return False,None
	return True,xy[M]
	#test for even distribution
	
		
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
		#subtract mean to get better numeric stability...
		xy_t=bd_pts.mean(axis=0)
		xy=bd_pts-xy_t
		a_poly-=xy_t
		#now find those corners!
		lines_ok=dict()
		found_lines=dict()
		for vertex in xrange(a_poly.shape[0]-1): #check line emanating from vertex...
			p1=a_poly[vertex]
			p2=a_poly[vertex+1]
			ok,pts=check_distribution(p1,p2,xy)
			lines_ok[vertex]=(ok,pts)
		#now find corners
		vertex=0 #handle the 0'th corner specially...
		while vertex<a_poly.shape[0]-2:
			if lines_ok[vertex][0] and lines_ok[vertex+1][0]: #proceed
				print("%s\nCorner %d should be findable..." %("+"*50,vertex+1))
				print("Finding line %d" %vertex)
				if vertex in found_lines:
					print("Already found, using that...")
					fmax=found_lines[vertex]
				else:
					pts=lines_ok[vertex][1]
					p1=a_poly[vertex]
					p2=a_poly[vertex+1]
					fmax=find_line(p1,p2,pts)
					found_lines[vertex]=fmax
				vertex+=1
				print("Finding line %d" %vertex)
				if vertex in found_lines:
					print("Already found, using that...")
					fmax=found_lines[vertex]
				else:
					pts=lines_ok[vertex][1]
					p1=a_poly[vertex]
					p2=a_poly[vertex+1]
					fmax=find_line(p1,p2,pts)
					found_lines[vertex]=fmax
				
			else:
				vertex+=2
		if lines_ok[0][0] and lines_ok[a_poly.shape[0]-2]:
			print("Corner 0 should also be findable...")
		plot_points(a_poly,xy)
			
			

			
			
			
		
		
	


if __name__=="__main__":
	main(sys.argv)