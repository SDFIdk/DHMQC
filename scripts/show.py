#####################
## Demo script which loads, grids and shows a pointcloud
######################
import sys
import pointcloud
import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
pc=pointcloud.fromLAS(sys.argv[1])
pc=pc.cut_to_z_interval(-20,200)
pc.triangulate()
g=pc.get_grid(800,800,crop=10,nd_val=-30)
bbox=g.get_bounds()
im=plt.imshow(g.grid,extent=(bbox[0],bbox[2],bbox[3],bbox[1]))
plt.colorbar(im)
plt.show()