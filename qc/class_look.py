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
##############
## Super simple script for visual inspection of classification and geometry in polygons
## use -3d as arg to view in 3d also....
##############
import sys,os
from thatsDEM import pointcloud, vector_io, array_geometry
import numpy as np
import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
c_to_color={1:"red",2:"green",3:"yellow",5:"cyan",7:"pink",11:"orange"}
def plot(pc,poly,den):
	plt.figure()
	cs=pc.get_classes()
	for c in cs:
		pcc=pc.cut_to_class(c)
		if c in c_to_color:
			col=c_to_color[c]
		else:
			col="blue"
		plt.plot(pcc.xy[:,0],pcc.xy[:,1],".",label="class %d" %c,color=col)
	plt.plot(poly[0][:,0],poly[0][:,1],linewidth=2.5,color="black")
	plt.axis("equal")
	plt.legend()
	plt.xlabel("Point density: %.3f" %den)
	plt.show()

def plot3d(pc):
	fig = plt.figure()
	ax = Axes3D(fig)
	cs=pc.get_classes()
	for c in cs:
		pcc=pc.cut_to_class(c)
		if c in c_to_color:
			col=c_to_color[c]
		else:
			col="black"
		ax.scatter(pcc.xy[:,0], pcc.xy[:,1], pcc.z,s=2.8,c=col)
	#pc=pc.cut_to_class(1)
	#pc.triangulate()
	#ax.plot_trisurf(pc.xy[:,0],pc.xy[:,1],pc.z,triangles=pc.triangulation.get_triangles(np.arange(0,pc.triangulation.ntrig)))
	plt.show()

def usage():
	print("Call:\n%s <las_file> <polygon_file> -3d" %os.path.basename(sys.argv[0]))
	print("-3d is optional - use to show a 3d plot also...")
	sys.exit()
	
def main(args):
	lasname=args[1]
	polyname=args[2]
	pc=pointcloud.fromLAS(lasname)
	do_3d="-3d" in args
	polys=vector_io.get_geometries(polyname)
	for poly in polys:
		a_poly=array_geometry.ogrgeom2array(poly)
		poly_b=poly.Buffer(4.0)
		a_poly_b=array_geometry.ogrgeom2array(poly_b)
		pcp=pc.cut_to_polygon(a_poly_b)
		#calculate point density...
		den=pcp.get_size()/poly_b.Area()
		plot(pcp,a_poly,den)
		if do_3d:
			plot3d(pcp)
		
	
	
if __name__=="__main__":
	main(sys.argv)
			