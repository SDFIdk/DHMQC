import sys,os 
import thatsDEM.pointcloud as pc

#mypc = pc.fromLAS("c://dev//dhmqc//demo//1km_6165_449.las")
mypc=pc.fromLAS(sys.argv[1])
print "Size:          "+str(mypc.get_size())
print "Classes:       "+str(mypc.get_classes())
print "XY bounds:     "+str(mypc.get_bounds())
print "Z bounds:      "+str(mypc.get_z_bounds())

mypc.triangulate()





