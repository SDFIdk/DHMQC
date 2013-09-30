import sys,os
import numpy as np
import shapely.geometry as shg
from triangle import triangle
from slash import slash
from osgeo import ogr

#Trianguler alle striber
#For alle striber(s punkter p_i=1 til n), goer...
#Ligger p_i taet paa vej-vertice?
#Hvis ja, interpoler 
#opsaml i array (punkt_id, fra_stribe, maalt z, interpoleret z)


#print sys.argv[2]
ds = ogr.Open(sys.argv[2])
print ds.GetLayer(0)

sys.exit()
 
# pointer to file. 
lasf=slash.LasFile(sys.argv[1])

# header of las file is read and the number of points are printed
print("%d points in %s" %(lasf.get_number_of_records(),sys.argv[1]))

# The las file is read into xy (planar coordinates), z (height) and c (classes)
xy,z,c,pid=lasf.read_records()

lasf.close()

#Empty dictionary defined
triangulations = dict()

for id in np.unique(pid):
	#numpy is used to return an array where point source id is the current number and class 2 (ground)
	I=np.where(np.logical_and(pid==id, c==2))[0]
	if I.size <100: 
		continue
	xyi = xy[I]
	zi  =  z[I]
	print I.size
	print id
	tri = triangle.Triangulation(xyi)
	tri.basez = zi
	triangulations[id]=tri
	
#We are being nice - cleaning up!
del xy
del z
del c
del pid
	
#Just to check that the triangulations have been stored in dictionary	
for id in triangulations:
	tri = triangulations[id]
	print tri.inspect_index()
	
	
	
del triangulations	

halt

#for id in triangulations:
#	del triangulations[id]	
	
#sys.exit()
#halt


#





# python zcheck.py C:\dev\dhmqc\demo\1km_6165_449.las C:\dev\dhmqc\demo\1km_6165_449.shp


	
	
	
	
	


