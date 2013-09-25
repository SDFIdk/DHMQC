import sys,os
import numpy as np
from triangle import triangle
from slash import slash



#
#
# 
# pointer to file. 
lasf=slash.LasFile(sys.argv[1])

# header of las file is read and the number of points are printed
print("%d points in %s" %(lasf.get_number_of_records(),sys.argv[1]))

# The las file is read into xy (planar coordinates), z (height) and c (classes)
xy,z,c=lasf.read_records()


# Minimum and maximum is found
x1,y1=xy.min(axis=0)
x2,y2=xy.max(axis=0)
z1=z.min()
z2=z.max()
print("XY: %.2f %.2f %.2f %.2f, Z: %.2f %.2f %.2f" %(x1,y1,x2,y2,z1,z2,z.mean()))
print("classes: %s" %np.unique(c))
    


tri=triangle.Triangulation(xy)

# 448050.00 6165010.00
#my_xy = np.array([448050.00, 6165010.00]).reshape((1,2)).copy()
my_xy = np.array([428050.00, 6165010.00]).reshape((1,2)).copy()

print my_xy.shape
print my_xy.dtype
print my_xy.flags
z_int=tri.interpolate(z,my_xy)
print z_int


python test.py C:\data\lasupload\las\1km_6165_448.las


