######################################################################################
## Find planes - works for 'simple houses' etc...
## Useful for finding house edges (where points fall of a plane) and roof 'ridges', where planes intersect...
## 
## Houses with parallel roof patches at different heights are problematic - would be better split out into more input polygons...
## work in progress...
######################################################################################

import sys,os,time
from thatsDEM import pointcloud, vector_io, array_geometry, report
import numpy as np
import  thatsDEM.dhmqc_constants as constants
from math import degrees,radians,acos,sqrt,cos,sin,atan,tan
import math
from utils.osutils import ArgumentParser
from find_planes import *
DEBUG="-debug" in sys.argv
#z-interval to restrict the pointcloud to.
Z_MIN=constants.z_min_terrain
Z_MAX=constants.z_max_terrain+30
LINE_RAD=5   #2*LINE_RAD lines to represent line geoms...
cut_to=[constants.building,constants.surface] #hmm try to only use building classifications here - should be less noisy!





progname=os.path.basename(__file__).replace(".pyc",".py")

parser=ArgumentParser(description="Check relative stripwise displacement of roofridges.",prog=progname)
#Argument handling

parser.add_argument("-use_all",action="store_true",help="Check all buildings. Else only check those with 4 corners.")
parser.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
parser.add_argument("-class",dest="cut_class",type=int,default=cut_to,help="Inspect points of this class - defaults to 'surface' and 'building'")
parser.add_argument("-sloppy",action="store_true",help="Use all buildings - no geometry restrictions (at all).")
parser.add_argument("-search_factor",type=float,default=1,help="Increase/decrease search factor - may result in larger computational time.")
parser.add_argument("-debug",action="store_true",help="Increase verbosity...")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("build_polys",help="input reference building polygons.")


def usage():
	parser.print_help()


		

#Now works for 'simple' houses...	
def main(args):
	pargs=parser.parse_args(args[1:])
	lasname=pargs.las_file
	polyname=pargs.build_polys
	kmname=constants.get_tilename(lasname)
	print("Running %s on block: %s, %s" %(os.path.basename(args[0]),kmname,time.asctime()))
	reporter=report.ReportRoofridgeStripCheck(pargs.use_local)
	cut_class=pargs.cut_class
	#default step values for search...
	steps1=30
	steps2=13
	search_factor=pargs.search_factor
	if search_factor!=1:
		#can turn search steps up or down
		f=search_factor
		steps1=int(f*steps1)
		steps2=int(f*steps2)
		print("Incresing search factor by: %.2f" %f)
		print("Running time will increase exponentionally with search factor...")
	pc=pointcloud.fromLAS(lasname).cut_to_class(cut_class).cut_to_z_interval(Z_MIN,Z_MAX)
	polys=vector_io.get_geometries(polyname)
	fn=0
	sl="+"*60
	is_sloppy=pargs.sloppy
	use_all=pargs.use_all
	for poly in polys:
		print(sl)
		fn+=1
		print("Checking feature number %d" %fn)
		a_poly=array_geometry.ogrgeom2array(poly)
		if (len(a_poly)>1 or a_poly[0].shape[0]!=5) and (not use_all) and (not is_sloppy): #secret argument to use all buildings...
			print("Only houses with 4 corners accepted... continuing...")
			continue
		pcp=pc.cut_to_polygon(a_poly)
		strips=pcp.get_pids()
		if len(strips)!=2:
			print("Not exactly two overlapping strips... continuing...")
			continue
		#Go to a more numerically stable coord system - from now on only consider outer ring...
		a_poly=a_poly[0]
		xy_t=a_poly.mean(axis=0) #center of mass system
		a_poly-=xy_t
		lines=[] # for storing the two found lines...
		for id in strips:
			print("-*-"*15)
			print("Looking at strip %d" %id)
			pcp_=pcp.cut_to_strip(id)
			if (pcp_.get_size()<500 and (not is_sloppy)) or (pcp_.get_size()<10): #hmmm, these consts should perhaps be made more visible...
				print("Few points in polygon... %d" %pcp_.get_size())
				continue
			pcp_.xy-=xy_t
			pcp_.triangulate()
			geom=pcp_.get_triangle_geometry()
			m=geom[:,1].mean()
			sd=geom[:,1].std()
			if (m>1.5 or 0.5*sd>m) and (not is_sloppy):
				print("Feature %d, strip %d, bad geometry...." %(fn,id))
				break
			planes=cluster(pcp_,steps1,steps2)
			if len(planes)<2:
				print("Feature %d, strip %d, didn't find enough planes..." %(fn,id))
			pair,equation=find_planar_pairs(planes)
			if pair is not None:
				p1=planes[pair[0]]
				p2=planes[pair[1]]
				print("%s" %("*"*60))
				print("Statistics for feature %d" %fn)
				if True: #always do this, similar structure to roof_ridge_alignment though...
					#Now we need to find some points on the line near the house... (0,0) is the center of mass
					norm_normal=equation[0]**2+equation[1]**2
					if norm_normal<1e-10:
						print("Numeric instablity, small normal")
						break
					cm_line=np.asarray(equation[:2])*(equation[2]/norm_normal)  #this should be on the line
					line_dir=np.asarray((-equation[1],equation[0]))/(sqrt(norm_normal))
					end1=cm_line+line_dir*LINE_RAD
					end2=cm_line-line_dir*LINE_RAD
					intersections=np.vstack((end1,end2))
					line_x=intersections[:,0]
					line_y=intersections[:,1]
					z_vals=p1[0]*intersections[:,0]+p1[1]*intersections[:,1]+p1[2]
					if abs(z_vals[0]-z_vals[1])>0.01:
						print("Numeric instabilty for z-calculation...")
					z_val=float(np.mean(z_vals))
					print("Z for intersection is %.2f m" %z_val)
					#transform back to real coords
					line_x+=xy_t[0]
					line_y+=xy_t[1]
					wkt="LINESTRING(%.3f %.3f %.3f, %.3f %.3f %.3f)" %(line_x[0],line_y[0],z_val,line_x[1],line_y[1],z_val)
					print("WKT: %s" %wkt)
					lines.append([id,wkt,z_val,cm_line,line_dir])
					
				else:
					print("Hmmm - something wrong, didn't get exactly two intersections...")
					break
		if len(lines)==2:
			#check for parallelity
			dir1=lines[0][4]
			dir2=lines[1][4]
			id1=lines[0][0]
			id2=lines[1][0]
			z1=lines[0][2]
			z2=lines[1][2]
			if abs(z1-z2)>0.5:
				print("Large difference in z-values for the two lines!")
			else:
				ids="{0:d}_{1:d}".format(id1,id2)
				inner_prod=(lines[0][4]*lines[1][4]).sum()
				inner_prod=max(-1,inner_prod)
				inner_prod=min(1,inner_prod)
				if DEBUG:
					print("Inner product: %.4f" %inner_prod)
				ang=abs(degrees(acos(inner_prod)))
				if (ang>175):
					ang=abs(180-ang)
				if ang<15:
					v=(lines[0][3]-lines[1][3])
					d=np.sqrt((v**2).sum())
					if d<5:
						for line in lines:
							reporter.report(kmname,id1,id2,ids,d,ang,line[2],wkt_geom=line[1])
					else:
						print("Large distance between centers %s, %s, %.2f" %(lines[0][3],lines[1][3],d))
				else:
					print("Pair found - but not very well aligned - angle: %.2f" %ang)
		else:
			print("Pair not found...")
			
		


if __name__=="__main__":
	main(sys.argv)