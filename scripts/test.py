import sys,os
import numpy as np
from thatsDEM import triangle,slash,array_factory




#
#
# 
# pointer to file. 
lasf=slash.LasFile(sys.argv[1])

# header of las file is read and the number of points are printed
print("%d points in %s" %(lasf.get_number_of_records(),sys.argv[1]))

# The las file is read into xy (planar coordinates), z (height) and c (classes)
r=lasf.read_records()
xy=r["xy"]
z=r["z"]
c=r["c"]
pid=r["pid"]

# Minimum and maximum is found
x1,y1=xy.min(axis=0)
x2,y2=xy.max(axis=0)
z1=z.min()
z2=z.max()
print("XY: %.2f %.2f %.2f %.2f, Z: %.2f %.2f %.2f" %(x1,y1,x2,y2,z1,z2,z.mean()))
print("classes: %s" %np.unique(c))
print("point ids: %s" %np.unique(pid))    


tri=triangle.Triangulation(xy)

# 448050.00 6165010.00
#my_xy = np.array([448050.00, 6165010.00]).reshape((1,2)).copy()
my_xy = array_factory.point_factory([428050.00, 6165010.00])
print("The factory function gives us an array of the right type - possible by making a copy:")
print my_xy.shape
print my_xy.dtype
print my_xy.flags
z_int=tri.interpolate(z,my_xy)
print z_int


# python test.py ..\demo\1km_6164_452.las


