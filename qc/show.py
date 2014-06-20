#####################
## Demo script which loads, grids and shows a pointcloud
######################
#This is stable branch!
import sys,os
import thatsDEM.pointcloud as pointcloud
import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
pc=pointcloud.fromLAS(sys.argv[1])
pc=pc.cut_to_z_interval(-20,200)
pc.triangulate()
z1,z2=pc.get_z_bounds()
nd_val=int(z1)-1
g=pc.get_grid(800,800,crop=10,nd_val=nd_val)
bbox=g.get_bounds()
im=plt.imshow(g.grid,extent=(bbox[0],bbox[2],bbox[3],bbox[1]))
plt.imshow(g.get_hillshade().grid,extent=(bbox[0],bbox[2],bbox[3],bbox[1]),alpha=0.5,cmap=matplotlib.cm.gray)
plt.colorbar(im)
plt.title("Plot of %s, nd_val is %d" %(os.path.basename(sys.argv[1]),nd_val))
plt.show()