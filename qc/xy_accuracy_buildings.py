# Copyright (c) 2015-2016, Danish Geodata Agency <gst@gst.dk>
# Copyright (c) 2016, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
####################
## Find planes - works for 'simple houses' etc...
## Useful for finding house edges (where points fall of a plane) and roof 'ridges', where planes intersect...
## work in progress...
###########################

from __future__ import absolute_import
from __future__ import print_function
import sys,os,time
from qc.thatsDEM import pointcloud, vector_io, array_geometry
from qc.db import report
from . import dhmqc_constants as constants
import numpy as np
from math import degrees,radians,acos,tan
from qc.utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
from six.moves import range
DEBUG="-debug" in sys.argv
if DEBUG:
	import matplotlib
	matplotlib.use("Qt4Agg")
	import matplotlib.pyplot as plt
	from mpl_toolkits.mplot3d import Axes3D

#some global params for finding house edges...
cut_angle=45.0
z_limit=2.0
cut_to_classes=[constants.terrain,constants.surface,constants.building]

progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Check accuracy relative to input polygons by finding house corners.",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
#add some arguments below
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database)",type=str)
parser.add_argument("-debug",help="debug",action="store_true")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("poly_data",help="input reference data connection string (e.g to a db, or just a path to a shapefile).")

def usage():
	parser.print_help()

#hmmm - np.dot is just weird - might be better to use that though...
def helmert2d(xy1,xy2):
	N1=(xy1**2).sum()
	N2=(xy2**2).sum()
	S1=xy1.sum(axis=0)
	S2=xy2.sum(axis=0)
	D=(xy1*xy2).sum()
	A=np.asarray(((N1,S1[0],S1[1]),(S1[0],xy1.shape[0],0),(S1[1],0,xy1.shape[0])))
	B=(D,S2[0],S2[1])
	return np.linalg.solve(A,B)

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
	print(("Pre: %.3f, %.4f, %.4f, %.4f" %(angle,N[0],N[1],c)))
	found=search(pts,angle-3,angle+3,30)
	print(("Post: %.3f, %.4f, %.4f, %.4f" %(found[3],found[0],found[1],found[2])))
	
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
	rot=found[3]-angle
	return np.asarray(found[:-1]),rot #return line and rotation...

#brute force - todo: real linear regression...
def search(xy,v1=0,v2=180,steps=30):
	V=np.radians(np.linspace(v1,v2,steps)) #angles in RP^1 (ie spanning not more than 180 dg)
	A=np.cos(V)
	B=np.sin(V)
	best=1e6
	found=None
	for i in range(A.shape[0]):
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

def get_intersection(line1,line2):
	AB=np.row_stack((line1,line2))
	xy=np.linalg.solve(AB[:,0:2],AB[:,2])
	return xy


#test for even distribution
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
	#print("Fraction of points 'close' to line %.3f" %f)
	h,bins=np.histogram(p,n_bins)
	h=h.astype(np.float64)/p.size
	if (h<0.05).sum()>3:
		print("Uneven distribution!")
		return False,None
	return True,xy[M]

# triangle vertices 0123 	
	
def get_line_data(vertex,lines_ok,found_lines,a_poly):	
	vertex=vertex % int(a_poly.shape[0]-1) #do a modulus to get back to line 0 when we need to check the 0'th corner...
	print(("Finding line %d" %vertex))
	if vertex in found_lines:
		print("Already found, using that...")
		line1,rot=found_lines[vertex]
	else:
		pts=lines_ok[vertex][1]
		p1=a_poly[vertex]
		p2=a_poly[vertex+1]
		line1,rot=find_line(p1,p2,pts)
		found_lines[vertex]=(line1,rot)
	print(("Line %d is rotated: %.3f dg" %(vertex,rot)))
	return line1

def find_corner(vertex,lines_ok,found_lines,a_poly):
	line1=get_line_data(vertex,lines_ok,found_lines,a_poly)
	vertex+=1
	line2=get_line_data(vertex,lines_ok,found_lines,a_poly)
	#now solve for the intersection
	corner_post=get_intersection(line1,line2)
	corner_pre=a_poly[vertex]
	dxy=corner_post-corner_pre
	ndxy=np.sqrt(dxy.dot(dxy))
	print("*** Result ***")
	print(("Found intersection is %s, polygon vertex: %s" %(corner_post,corner_pre)))
	print(("DXY: %s" %(dxy)))
	print(("Norm: %s"%(ndxy)))
	#print a_poly[vertex],vertex
	return corner_post

def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception as e:
		print((str(e)))
		return 1
	kmname=constants.get_tilename(pargs.las_file)
	print(("Running %s on block: %s, %s" %(progname,kmname,time.asctime())))
	lasname=pargs.las_file
	polyname=pargs.poly_data
	use_local=pargs.use_local
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportBuildingAbsposCheck(use_local)
	##################################
	pc=pointcloud.fromAny(lasname).cut_to_class(cut_to_classes)
	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception as e:
		print("Could not get extent from tilename.")
		extent=None
	polys=vector_io.get_geometries(polyname,pargs.layername,pargs.layersql,extent)
	fn=0
	sl="-"*65
	for poly in polys:
		n_corners_found=0
		fn+=1
		print(("%s\nChecking feature %d\n%s\n"%(sl,fn,sl)))
		a_poly=array_geometry.ogrgeom2array(poly)
		pcp=pc.cut_to_polygon(a_poly)
		if pcp.get_size()<500:
			print("Few points in polygon...")
			continue
		a_poly=a_poly[0]
		all_post=np.zeros_like(a_poly) #array of vertices found
		all_pre=np.zeros_like(a_poly)   #array of vertices in polygon, correpsonding to found...
		pcp.triangulate()
		geom=pcp.get_triangle_geometry()
		m=geom[:,1].mean()
		sd=geom[:,1].std()
		if (m>1.5 or 0.5*sd>m):
			print(("Feature %d, bad geometry...." %fn))
			print(("{} {}".format(m, sd)))
			continue
		#geom is ok - we proceed with a buffer around da house
		poly_buf=poly.Buffer(2.0)
		a_poly2=array_geometry.ogrgeom2array(poly_buf)
		pcp=pc.cut_to_polygon(a_poly2)
		print(("Points in buffer: %d" %pcp.get_size()))
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
		if DEBUG:
			plot_points(a_poly,xy)
		#now find those corners!
		lines_ok=dict()
		found_lines=dict()
		for vertex in range(a_poly.shape[0]-1): #check line emanating from vertex...
			p1=a_poly[vertex]
			p2=a_poly[vertex+1]
			ok,pts=check_distribution(p1,p2,xy)
			lines_ok[vertex]=(ok,pts)
		#now find corners
		vertex=0 #handle the 0'th corner specially...
		while vertex<a_poly.shape[0]-2:
			if lines_ok[vertex][0] and lines_ok[vertex+1][0]: #proceed
				print(("%s\nCorner %d should be findable..." %("+"*50,vertex+1)))
				corner_found=find_corner(vertex,lines_ok,found_lines,a_poly)
				all_pre[n_corners_found]=a_poly[vertex+1]
				all_post[n_corners_found]=corner_found
				#print a_poly[vertex+1],corner_found,vertex
				n_corners_found+=1
				vertex+=1
			else: #skip to next findable corner
				vertex+=2
		if lines_ok[0][0] and lines_ok[a_poly.shape[0]-2][0]:
			print("Corner 0 should also be findable...")
			corner_found=find_corner(a_poly.shape[0]-2,lines_ok,found_lines,a_poly)
			all_pre[n_corners_found]=a_poly[0]
			all_post[n_corners_found]=corner_found
			n_corners_found+=1
		print(("\n********** In total for feature %d:" %fn))
		print(("Corners found: %d" %n_corners_found))
		if n_corners_found>0:
			all_post=all_post[:n_corners_found]
			all_pre=all_pre[:n_corners_found]
			all_dxy=all_post-all_pre
			mdxy=all_dxy.mean(axis=0)
			sdxy=np.std(all_dxy,axis=0)
			ndxy=norm(all_dxy)
			params=(1,mdxy[0],mdxy[1])
			print(("Mean dxy:      %.3f, %.3f" %(mdxy[0],mdxy[1])))
			print(("Sd      :      %.3f, %.3f"  %(sdxy[0],sdxy[1])))
			print(("Max absolute : %.3f m"   %(ndxy.max())))
			print(("Mean absolute: %.3f m"   %(ndxy.mean())))
			if n_corners_found>1:
				print("Helmert transformation (pre to post):")
				params=helmert2d(all_pre,all_post)
				print(("Scale:  %.5f ppm" %((params[0]-1)*1e6)))
				print(("dx:     %.3f m" %params[1]))
				print(("dy:     %.3f m" %params[2]))
				print("Residuals:")
				all_post_=params[0]*all_pre+params[1:]
				all_dxy=all_post-all_post_
				mdxy=all_dxy.mean(axis=0)
				sdxy=np.std(all_dxy,axis=0)
				ndxy=norm(all_dxy)
				print(("Mean dxy:      %.3f, %.3f" %(mdxy[0],mdxy[1])))
				print(("Sd      :      %.3f, %.3f"  %(sdxy[0],sdxy[1])))
				print(("Max absolute : %.3f m"   %(ndxy.max())))
				print(("Mean absolute: %.3f m"   %(ndxy.mean())))
			reporter.report(kmname,params[0],params[1],params[2],n_corners_found,ogr_geom=poly)
		
		
			
			

if __name__=="__main__":
	main(sys.argv)
