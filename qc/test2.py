import sys,os 
import thatsDEM.pointcloud as pc
import numpy as np

#mypc = pc.fromLAS("c://dev//dhmqc//demo//1km_6165_449.las")
mypc=pc.fromLAS(sys.argv[1])
print "Size:          "+str(mypc.get_size())
print "Classes:       "+str(mypc.get_classes())
print "Strip ids:     "+str(mypc.get_strips())
print "XY bounds:     "+str(mypc.get_bounds())
print "Z bounds:      "+str(mypc.get_z_bounds())

mypc.triangulate()
#generate some random points
xy=np.random.rand(100,2)*20+mypc.get_bounds()[0:2]
#set a validty mask on triangles
mypc.calculate_validity_mask(60,5,3)
mask=mypc.get_validity_mask()
n_good=mask.sum()
print "Number of triangles with slope less than 60 deg, xy-bbox<5m and z-bbox<3m: %d, fraction: %.3f" %(n_good,n_good/float(mask.size))
z1=mypc.interpolate(xy,nd_val=-100)
z2=mypc.controlled_interpolation(xy,nd_val=-100)
print "Number of no-data values for 100 random points using all triangles: %d" %((z1==-100).sum())
print "Number of no-data values for 100 random points using only valid triangles: %d" %((z2==-100).sum())




