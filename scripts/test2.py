import sys,os 
import pointcloud as pc

mypc = pc.las2pointcloud("c://dev//dhmqc//demo//1km_6165_449.las")

print "Size:          "+str(mypc.get_size())
print "Classes:       "+str(mypc.get_classes())
print "XY bounds:     "+str(mypc.get_bounds())
print "Z bounds:      "+str(mypc.get_z_bounds())

mypc.triangulate()





