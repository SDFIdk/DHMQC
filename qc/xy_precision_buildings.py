# Copyright (c) 2015, Danish Geodata Agency <gst@gst.dk>
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

import sys,os,time
from thatsDEM import pointcloud, vector_io, array_geometry
from db import report
import dhmqc_constants as constants
import numpy as np
from math import degrees,radians,acos,tan
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
DEBUG="-debug" in sys.argv
LIGHT_DEBUG="-light_debug" in sys.argv
if DEBUG or LIGHT_DEBUG:
	import matplotlib
	matplotlib.use("Qt4Agg")
	import matplotlib.pyplot as plt
	from mpl_toolkits.mplot3d import Axes3D

#some global params for finding house edges...
cut_angle=45.0
z_limit=2.0
cut_to_classes=[constants.terrain,constants.surface]
TOL_CORNER=1.0   #Tolerance for distance between found corner and polygon corner before we consider it as 'found'
progname=os.path.basename(__file__).replace(".pyc",".py")
#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Check horisontal precision by finding house corners in strips.",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
#add some arguments below
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database)")
parser.add_argument("-debug",help="debug",action="store_true")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("poly_data",help="input reference data connection string (e.g to a db, or just a path to a shapefile).")

def usage():
	parser.print_help()

#hmmm - np.dot is just weird - might be better to use that though...
#transformation from 1->2 ?
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

def norm2(x):
	return np.sqrt((x**2).sum())

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
	found=search(pts,angle-3,angle+3,30)
	print("Post: %.3f, %.4f, %.4f, %.4f" %(found[3],found[0],found[1],found[2]))
	
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

def plot3(pts):
	legends=["corners1","corners2","1->2"]
	colors=["red","green","blue"]
	plt.close("all")
	plt.figure()
	plt.axis("equal")
	for i,xy in enumerate(pts[:3]):
		plt.scatter(xy[:,0],xy[:,1],label=legends[i],color=colors[i])
	plt.legend()
	plt.show()

def get_intersection(line1,line2):
	AB=np.row_stack((line1,line2))
	xy=np.linalg.solve(AB[:,0:2],AB[:,2])
	return xy


#test for even distribution
def check_distribution(p1,p2,xy):
	if xy.shape[0]==0:
		return False,None
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
	print("Finding line %d" %vertex)
	if vertex in found_lines:
		print("Already found, using that...")
		line1,rot=found_lines[vertex]
	else:
		pts=lines_ok[vertex][1]
		p1=a_poly[vertex]
		p2=a_poly[vertex+1]
		line1,rot=find_line(p1,p2,pts)
		found_lines[vertex]=(line1,rot)
	print("Line %d is rotated: %.3f dg" %(vertex,rot))
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
	print("Found intersection is %s, polygon vertex: %s" %(corner_post,corner_pre))
	print("DXY: %s" %(dxy))
	print("Norm: %s"%(ndxy))
	#print a_poly[vertex],vertex
	return corner_post

def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception,e:
		print(str(e))
		return 1
	kmname=constants.get_tilename(pargs.las_file)
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	lasname=pargs.las_file
	polyname=pargs.poly_data
	use_local=pargs.use_local
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportBuildingRelposCheck(use_local)
	##################################
	pc=pointcloud.fromLAS(lasname).cut_to_z_interval(-10,200).cut_to_class(cut_to_classes)
	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception,e:
		print("Could not get extent from tilename.")
		extent=None
	polys=vector_io.get_geometries(polyname)
	fn=0
	sl="-"*65
	pcs=dict()
	for id in pc.get_pids():
		print("%s\n" %("+"*70))
		print("Strip id: %d" %id)
		pc_=pc.cut_to_strip(id)
		if pc_.get_size()>500:
			pcs[id]=pc_
		else:
			print("Not enough points....")
	del pc
	done=[]
	for id1 in pcs:
		pc1=pcs[id1]
		for id2 in pcs:
			if id1==id2 or (id1,id2) in done or (id2,id1) in done:
				continue
			done.append((id1,id2))
			pc2=pcs[id2]
			ml="-"*70
			print("%s\nChecking strip %d against strip %d\n%s" %(ml,id1,id2,ml))
			if not pc1.might_overlap(pc2):
				if DEBUG:
					print("Strip %d and strip %d does not seem to overlap. Continuing..." %(id1,id2))
					print("DEBUG: Strip1 bounds:\n%s\nStrip2 bounds:\n%s" %(pc1.get_bounds(),pc2.get_bounds())) 
				continue
			for poly in polys:
				centroid=poly.Centroid()
				centroid.FlattenTo2D()
				if LIGHT_DEBUG:
					print("Geom type: %s" %centroid.GetGeometryName())
				n_corners_found=0
				fn+=1
				print("%s\nChecking feature %d\n%s\n"%(sl,fn,sl))
				a_poly=array_geometry.ogrgeom2array(poly)
				pcp1=pc1.cut_to_polygon(a_poly)
				if pcp1.get_size()<300:
					print("Few (%d) points in polygon..." %pcp1.get_size())
					continue
				pcp2=pc2.cut_to_polygon(a_poly)
				if pcp2.get_size()<300:
					print("Few (%d) points in polygon..." %pcp2.get_size())
					continue
				a_poly=a_poly[0]
				poly_buf=poly.Buffer(2.0)
				xy_t=a_poly.mean(axis=0) #transform later to center of mass system for numerical stability...
				#transform a_poly coords to center of mass system here
				a_poly-=xy_t
				a_poly2=array_geometry.ogrgeom2array(poly_buf)
				#dicts to store the found corners in the two strips...
				found1=dict()
				found2=dict()
				for pc,pcp,store in [(pc1,pcp1,found1),(pc2,pcp2,found2)]:
					pcp.triangulate()
					geom=pcp.get_triangle_geometry()
					m=geom[:,1].mean()
					sd=geom[:,1].std()
					if (m>1.5 or 0.5*sd>m):
						print("Feature %d, bad geometry...." %fn)
						print m,sd
						break
					#geom is ok - we proceed with a buffer around da house
					pcp=pc.cut_to_polygon(a_poly2)
					######
					## Transform pointcloud to center of mass system here...
					#######
					pcp.xy-=xy_t
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
					xy=pcp.xy[bd_mask]
					
					
					print("Boundary points: %d" %xy.shape[0])
					if DEBUG:
						plot_points(a_poly,xy)
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
							corner_found=find_corner(vertex,lines_ok,found_lines,a_poly)
							diff=norm2(a_poly[vertex+1]-corner_found)
							if (diff<TOL_CORNER): #seems reasonable that this is a true corner...
								store[vertex+1]=corner_found
								n_corners_found+=1
							#print a_poly[vertex+1],corner_found,vertex
							vertex+=1
						else: #skip to next findable corner
							vertex+=2
					if lines_ok[0][0] and lines_ok[a_poly.shape[0]-2][0]:
						print("Corner 0 should also be findable...")
						corner_found=find_corner(a_poly.shape[0]-2,lines_ok,found_lines,a_poly)
						diff=norm2(a_poly[0]-corner_found)
						if (diff<TOL_CORNER): #seems reasonable that this is a true corner...
							store[0]=corner_found
							n_corners_found+=1
					print("Corners found: %d" %n_corners_found)
					if n_corners_found==0: #no need to do another check...
						break
				print("Found %d corners in strip %d, and %d corners in strip %d" %(len(found1),id1,len(found2),id2))
				if len(found1)>0 and len(found2)>0:
					match1=[]
					match2=[]
					for cn in found1:
						if cn in found2:
							match1.append(found1[cn])
							match2.append(found2[cn])
					if len(match1)>0:
						match1=np.array(match1)
						match2=np.array(match2)
						n_corners_found=match1.shape[0]
						print("\n********** In total for feature %d:" %fn)
						print("Corners found in both strips: %d" %n_corners_found)
						all_dxy=match1-match2
						mdxy=all_dxy.mean(axis=0)
						sdxy=np.std(all_dxy,axis=0)
						ndxy=norm(all_dxy)
						params=(1,mdxy[0],mdxy[1])
						print("Mean dxy:      %.3f, %.3f" %(mdxy[0],mdxy[1]))
						print("Sd      :      %.3f, %.3f"  %(sdxy[0],sdxy[1]))
						print("Max absolute : %.3f m"   %(ndxy.max()))
						print("Mean absolute: %.3f m"   %(ndxy.mean()))
						if n_corners_found>1:
							print("Helmert transformation (corners1 to corners2):")
							params=helmert2d(match1,match2) #2->1 or 1->2 ?
							print("Scale:  %.5f ppm" %((params[0]-1)*1e6))
							print("dx:     %.3f m" %params[1])
							print("dy:     %.3f m" %params[2])
							print("Residuals:")
							match2_=params[0]*match1+params[1:]
							all_dxy=match2_-match2
							mdxy_=all_dxy.mean(axis=0)
							sdxy_=np.std(all_dxy,axis=0)
							ndxy_=norm(all_dxy)
							if DEBUG or LIGHT_DEBUG:
								plot3([match1,match2,match2_])
							#center of mass distances only!!
							cm_vector=(match2.mean(axis=0)-match1.mean(axis=0))
							cm_dist=norm2(cm_vector)
							print("Mean dxy:      %.3f, %.3f" %(mdxy_[0],mdxy_[1]))
							print("Sd      :      %.3f, %.3f"  %(sdxy_[0],sdxy_[1]))
							print("Max absolute : %.3f m"   %(ndxy_.max()))
							print("Mean absolute: %.3f m"   %(ndxy_.mean()))
							reporter.report(kmname,id1,id2,cm_vector[0],cm_vector[1],cm_dist,params[0],params[1],params[2],sdxy_[0],sdxy_[1],n_corners_found,ogr_geom=centroid)
		
		
			
			

if __name__=="__main__":
	main(sys.argv)