######################################################################################
## Find planes - works for 'simple houses' etc...
## Useful for finding house edges (where points fall of a plane) and roof 'ridges', where planes intersect...
## 
## Houses with parallel roof patches at different heights are problematic - would be better split out into more input polygons...
## work in progress...
######################################################################################

import sys,os,time
from thatsDEM import pointcloud, vector_io, array_geometry, report
from utils.names import get_1km_name
import numpy as np
import dhmqc_constants as constants
from math import degrees,radians,acos
DEBUG="-debug" in sys.argv
#z-interval to restrict the pointcloud to.
Z_MIN=0
Z_MAX=250

cut_to=[constants.surface,constants.building]


if DEBUG:
	import matplotlib
	matplotlib.use("Qt4Agg")
	import matplotlib.pyplot as plt
	from mpl_toolkits.mplot3d import Axes3D

def usage():
	print("Call:\n%s <las_file> <polygon_file> (options)" %os.path.basename(sys.argv[0]))
	print("Options can be:")
	print("-use_all to check all buildings. Else only check those with 4 corners.")
	print("-use_local to force use of local database for reporting.")
	print("-class <c> to inspect points of class c - defaults to 'surface' defined by constants script.")
	print("-sloppy to not force any constraints...")
	print("-search_factor <f> to increase or decrease the search loop steps - warning: might increase running time a lot!")
	sys.exit()


#important here to have a relatively large bin size.... 0.2m seems ok.
def find_horisontal_planes(z,look_lim=0.2, bin_size=0.2):
	z1=z.min()
	z2=z.max()
	n=max(int(np.round(z2-z1)/bin_size),1)
	h,bins=np.histogram(z,n)
	h=h.astype(np.float64)/z.size
	#TODO: real clustering
	I=np.where(h>=look_lim)[0]  #the bins that are above fraction look_lim
	if I.size==0:
		return None,None
	bin_centers=bins[:-1]+np.diff(bins)
	return bin_centers[I],np.sum(h[I])
	
def search(a1,a2,b1,b2,xy,z,look_lim=0.1,bin_size=0.2,steps=15):
	A=np.linspace(a1,a2,steps)
	B=np.linspace(b1,b2,steps)
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
			if h[i]>look_lim: #and h[i]>3*h.mean(): #this one fucks it up...
				c_m=(bins[i]+bins[i+1])*0.5
				here=[a,b,c_m,h[i],alpha]   
				if h[i]>h_max:
					found_max=here
					h_max=h[i]
				found.append(here)
			
	return found_max,found


#A bit of parameter magic going on here,,,
#TODO: make the parameters more visible 
def cluster(pc,steps1=15,steps2=20): #number of steps affect running time and precsion of output...
	xy=pc.xy
	z=pc.z
	h_planes,h_frac=find_horisontal_planes(z)
	if h_planes is not None and h_frac>0.75:
		print("Seemingly a house with mostly flat roof at:")
		for z_h in h_planes:
			print("z=%.2f m" %z_h)
		return []
	fmax,found=search(-2.5,2.5,-2.5,2.5,xy,z,0.05,steps=steps1)
	print("Initial search resulted in %d planes." %len(found))
	final_candidates=[]
	if len(found)>0:
		for plane in found:
			if DEBUG:
				print("'Raw' candidate:\n%s" %(plane))
			a,b=plane[0],plane[1]
			fmax,found2=search(a-0.3,a+0.3,b-0.3,b+0.3,xy,z,0.05,0.1,steps=steps2) #slightly finer search
			#using only fmax, we wont find parallel planes
			if fmax is None:
				continue
			if DEBUG:
				print("After a closer look we get:\n%s" %(fmax))
			if fmax[3]>0.05: #at least 5 pct...
				replaced_other=False
				for i in range(len(final_candidates)):
					stored=final_candidates[i]
					if max(abs(fmax[0]-stored[0]),abs(fmax[1]-stored[1]))<0.1 and abs(fmax[2]-stored[2])<0.15 and fmax[3]>stored[3]: #check if a similar plane already stored
						final_candidates[i]=fmax #if so store the most popular of the two...
						replaced_other=True
						if DEBUG:
							print("Replacing...")
						break
				if not replaced_other:
					if DEBUG:
						print("Appending...")
					final_candidates.append(fmax)
				
		if DEBUG:
			print("Number of 'final candidates': %d" %len(final_candidates))
			for f in final_candidates:
				print("Plotting:\n%s" %(f))
				z1=f[0]*xy[:,0]+f[1]*xy[:,1]+f[2]
				plot3d(xy,z,z1)
	
	return final_candidates
		
def find_planar_pairs(planes):
	if len(planes)<2:
		return None,None
	
	print("Finding pairs in %d planes" %len(planes))
	best_score=1000
	best_pop=0.0000001
	pair=None
	eq=None
	z=None
	for i in range(len(planes)):
		p1=planes[i]
		for j in range(i+1,len(planes)):
			p2=planes[j]
			g_score=((p1[0]+p2[0])**2+(p1[1]+p2[1])**2)+2.0/(p1[-1]+p2[-1]) #bonus for being close, bonus for being steep
			pop=(p1[-2]+p2[-2])
			score=g_score/pop
			if score<best_score or ((best_score/score)>0.85 and pop/best_pop>1.5):
				pair=(i,j)
				best_score=score
				best_pop=pop
				
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


def plot_intersections(a_poly,intersections,line_x,line_y):
	plt.figure()
	plt.axis("equal")
	plt.plot(a_poly[:,0],a_poly[:,1],label="Polygon")
	plt.scatter(intersections[:,0],intersections[:,1],label="Intersections",color="red")
	plt.plot(line_x,line_y,label="Found 'roof ridge'")
	plt.legend()
	plt.show()

def get_intersections(poly,line):
	#hmmm - not many vertices, probably fast enough to run a python loop
	#TODO: test that all vertices are corners...
	intersections=[]
	distances=[]
	rotations=[]
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
			try:
				xy=np.linalg.solve(A,(c,line[2]))
			except Exception,e:
				print("Exception in linalg solver: %s" %(str(e)))
				continue
			xy_v=xy-poly[i]
			# check that we actually get something on the line...
			n_xy_v=np.sqrt((xy_v**2).sum())
			cosv=np.dot(v,xy_v)/(n_v*n_xy_v)
			if abs(cosv-1)<0.01 and n_xy_v/n_v<1.0:
				center=poly[i]+v*0.5
				d=np.sqrt(((center-xy)**2).sum())
				cosv=np.dot(n2,a_line)/(n_v*n_line)
				try:
					rot=degrees(acos(cosv))-90.0
				except Exception,e:
					print("Exception finding rotation: %s, numeric instabilty..." %(str(e)))
					continue
				print("Distance from intersection to line center: %.4f m" %d)
				print("Rotation:                                  %.4f dg" %rot)
				intersections.append(xy.tolist())
				distances.append(d)
				rotations.append(rot)
	return np.asarray(intersections),distances,rotations
		

#Now works for 'simple' houses...	
def main(args):
	if len(args)<3:
		usage()
	lasname=args[1]
	polyname=args[2]
	kmname=get_1km_name(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	use_local="-use_local" in args
	reporter=report.ReportRoofridgeCheck(use_local)
	if "-class" in args:
		cut_class=int(args[args.index("-class")+1])
	else:
		cut_class=cut_to
	#default step values for search...
	steps1=15
	steps2=20
	if "-search_factor" in args:
		#can turn search steps up or down
		f=float(args[args.index("-search_factor")+1])
		steps1=int(f*steps1)
		steps2=int(f*steps2)
		print("Incresing search factor by: %.2f" %f)
		print("Running time will increase exponentionally with search factor...")
	pc=pointcloud.fromLAS(lasname).cut_to_class(cut_class).cut_to_z_interval(Z_MIN,Z_MAX)
	polys=vector_io.get_geometries(polyname)
	fn=0
	sl="+"*60
	is_sloppy="-sloppy" in args
	for poly in polys:
		print(sl)
		fn+=1
		print("Checking feature number %d" %fn)
		a_poly=array_geometry.ogrgeom2array(poly)
		if (len(a_poly)>1 or a_poly[0].shape[0]!=5) and (not ("-use_all") in args) and (not is_sloppy): #secret argument to use all buildings...
			print("Only houses with 4 corners accepted... continuing...")
			continue
		pcp=pc.cut_to_polygon(a_poly)
		if (pcp.get_size()<500 and (not is_sloppy)) or (pcp.get_size()<10): #hmmm, these consts should perhaps be made more visible...
			print("Few points in polygon...")
			continue
		#Go to a more numerically stable coord system - from now on only consider outer ring...
		a_poly=a_poly[0]
		xy_t=a_poly.mean(axis=0)
		a_poly-=xy_t
		pcp.xy-=xy_t
		pcp.triangulate()
		geom=pcp.get_triangle_geometry()
		m=geom[:,1].mean()
		sd=geom[:,1].std()
		if (m>1.5 or 0.5*sd>m) and (not is_sloppy):
			print("Feature %d, bad geometry...." %fn)
			print m,sd
			continue
		planes=cluster(pcp,steps1,steps2)
		if len(planes)<2:
			print("Feature %d, didn't find enough planes..." %fn)
		pair,equation=find_planar_pairs(planes)
		if pair is not None:
			p1=planes[pair[0]]
			p2=planes[pair[1]]
			z1=p1[0]*pcp.xy[:,0]+p1[1]*pcp.xy[:,1]+p1[2]
			z2=p2[0]*pcp.xy[:,0]+p2[1]*pcp.xy[:,1]+p2[2]
			print("%s" %("*"*60))
			print("Statistics for feature %d" %fn)
			if DEBUG:
				plot3d(pcp.xy,pcp.z,z1,z2)
			intersections,distances,rotations=get_intersections(a_poly,equation)
			if intersections.shape[0]==2:
				line_x=intersections[:,0]
				line_y=intersections[:,1]
				z_vals=p1[0]*intersections[:,0]+p1[1]*intersections[:,1]+p1[2]
				if abs(z_vals[0]-z_vals[1])>0.01:
					print("Numeric instabilty for z-calculation...")
				z_val=float(np.mean(z_vals))
				print("Z for intersection is %.2f m" %z_val)
				if abs(equation[1])>1e-3:
					a=-equation[0]/equation[1]
					b=equation[2]/equation[1]
					line_y=a*line_x+b
				elif abs(equation[0])>1e-3:
					a=-equation[1]/equation[0]
					b=equation[2]/equation[0]
					line_x=a*line_y+b
				if DEBUG:
					plot_intersections(a_poly,intersections,line_x,line_y)
				#transform back to real coords
				line_x+=xy_t[0]
				line_y+=xy_t[1]
				wkt="LINESTRING(%.3f %.3f %.3f, %.3f %.3f %.3f)" %(line_x[0],line_y[0],z_val,line_x[1],line_y[1],z_val)
				print("WKT: %s" %wkt)
				reporter.report(kmname,rotations[0],distances[0],distances[1],wkt_geom=wkt)
			else:
				print("Hmmm - something wrong, didn't get exactly two intersections...")
		


if __name__=="__main__":
	main(sys.argv)